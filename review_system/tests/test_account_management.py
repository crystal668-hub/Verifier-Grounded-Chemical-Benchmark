from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as DBSession

from review_system.db import Base
from datetime import datetime, timezone

from review_system.main import beijing_isoformat, change_password, users
from review_system.models import PasswordChangeEvent, Session, User
from review_system.schemas import PasswordChangeIn
from review_system.security import create_session, hash_password, require_developer, verify_password


def test_user_can_change_own_password_without_revoking_sessions_and_with_audit():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with DBSession(engine, expire_on_commit=False) as database:
        user = User(username="reviewer", password_hash=hash_password("old-password"), role="collaborator")
        database.add(user)
        database.commit()
        create_session(database, user)

        result = change_password(PasswordChangeIn(current_password="old-password", new_password="new-password"), database, user, "request-1")

        assert result == {"ok": True, "changed": True, "idempotent_replay": False}
        assert verify_password("new-password", user.password_hash)
        assert not verify_password("old-password", user.password_hash)
        assert database.query(Session).filter_by(user_id=user.id).count() == 1
        assert database.query(PasswordChangeEvent).filter_by(user_id=user.id, request_id="request-1").count() == 1

        changed_hash = user.password_hash
        replay = change_password(PasswordChangeIn(current_password="old-password", new_password="new-password"), database, user, "request-1")
        assert replay == {"ok": True, "changed": False, "idempotent_replay": True}
        assert user.password_hash == changed_hash
        assert database.query(PasswordChangeEvent).filter_by(user_id=user.id).count() == 1

        semantic_replay = change_password(PasswordChangeIn(current_password="old-password", new_password="new-password"), database, user, "request-2")
        assert semantic_replay == {"ok": True, "changed": False, "idempotent_replay": True}
        assert user.password_hash == changed_hash
        assert database.query(PasswordChangeEvent).filter_by(user_id=user.id).count() == 1


def test_password_change_rejects_wrong_current_password():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with DBSession(engine, expire_on_commit=False) as database:
        user = User(username="reviewer", password_hash=hash_password("old-password"), role="collaborator")
        database.add(user)
        database.commit()

        with pytest.raises(HTTPException) as raised:
            change_password(PasswordChangeIn(current_password="wrong-password", new_password="new-password"), database, user, "request-wrong")
        assert raised.value.status_code == 400
        assert verify_password("old-password", user.password_hash)


def test_developer_user_list_includes_registration_information():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with DBSession(engine, expire_on_commit=False) as database:
        developer = User(username="admin", password_hash="hash", role="developer")
        collaborator = User(username="reviewer", password_hash="hash", role="collaborator", active=False)
        database.add_all([developer, collaborator])
        database.commit()

        result = users(database, developer)
        by_name = {item["username"]: item for item in result}
        assert by_name["admin"]["role"] == "developer"
        assert by_name["reviewer"]["active"] is False
        assert by_name["reviewer"]["created_at"] is not None
        assert by_name["reviewer"]["password_changed_at"] is None

        with pytest.raises(HTTPException) as raised:
            require_developer(collaborator)
        assert raised.value.status_code == 403


def test_account_timestamps_are_serialized_as_beijing_time():
    assert beijing_isoformat(datetime(2026, 9, 15, 8, 4, 11)) == "2026-09-15T16:04:11+08:00"
    assert beijing_isoformat(datetime(2026, 9, 15, 8, 4, 11, tzinfo=timezone.utc)) == "2026-09-15T16:04:11+08:00"
