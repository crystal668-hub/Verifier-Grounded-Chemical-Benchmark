from datetime import datetime, timedelta, timezone
from starlette.requests import Request
from starlette.responses import Response

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session as DBSession

from review_system import config
from review_system.db import Base
from review_system.models import Session, User
from review_system.main import register
from review_system.schemas import RegisterIn
from review_system.security import create_session, hash_password, revoke_user_sessions, session_token_hash, verify_password


def test_production_config_rejects_weak_settings(monkeypatch):
    monkeypatch.setattr(config, "ENVIRONMENT", "production")
    monkeypatch.setattr(config, "SECRET_KEY", "weak")
    monkeypatch.setattr(config, "COOKIE_SECURE", False)
    monkeypatch.setattr(config, "ADMIN_PASSWORD", "short")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        config.validate_production_config(database_is_empty=True)


def test_production_config_accepts_secure_existing_database(monkeypatch):
    monkeypatch.setattr(config, "ENVIRONMENT", "production")
    monkeypatch.setattr(config, "SECRET_KEY", "x" * 32)
    monkeypatch.setattr(config, "COOKIE_SECURE", True)
    monkeypatch.setattr(config, "ADMIN_PASSWORD", None)
    config.validate_production_config(database_is_empty=False)


def test_password_and_session_lifecycle():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with DBSession(engine, expire_on_commit=False) as database:
        user = User(username="reviewer", password_hash=hash_password("correct horse battery staple"), role="collaborator")
        database.add(user)
        database.commit()
        assert verify_password("correct horse battery staple", user.password_hash)
        assert not verify_password("wrong password", user.password_hash)
        token, csrf = create_session(database, user)
        session = database.get(Session, session_token_hash(token))
        assert session is not None
        assert session.csrf_token == csrf
        revoke_user_sessions(database, user.id)
        database.commit()
        assert database.get(Session, session_token_hash(token)) is None


def test_self_service_registration_creates_collaborator_and_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    request = Request({"type": "http", "method": "POST", "path": "/api/v1/auth/register", "headers": [], "client": ("127.0.0.1", 1), "scheme": "http"})
    response = Response()
    with DBSession(engine, expire_on_commit=False) as database:
        result = register(RegisterIn(username="  new-reviewer  ", password="123456"), request, response, database)
        user = database.scalar(select(User).where(User.username == "new-reviewer"))
        assert result["user"]["role"] == "collaborator"
        assert user is not None
        assert user.active is True
        assert database.query(Session).filter_by(user_id=user.id).count() == 1
        assert response.headers.get("set-cookie", "").startswith("review_session=")


def test_self_service_registration_rejects_password_shorter_than_six_characters():
    with pytest.raises(ValidationError):
        RegisterIn(username="reviewer", password="12345")


def test_self_service_registration_rejects_duplicate_username():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    request = Request({"type": "http", "method": "POST", "path": "/api/v1/auth/register", "headers": [], "client": ("127.0.0.1", 1), "scheme": "http"})
    with DBSession(engine, expire_on_commit=False) as database:
        database.add(User(username="reviewer", password_hash=hash_password("correct horse battery"), role="collaborator"))
        database.commit()
        with pytest.raises(HTTPException) as raised:
            register(RegisterIn(username="reviewer", password="another correct password"), request, Response(), database)
        assert getattr(raised.value, "status_code", None) == 409
