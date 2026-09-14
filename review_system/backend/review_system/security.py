import base64, hashlib, hmac, ipaddress, secrets
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Request
from sqlalchemy import delete
from sqlalchemy.orm import Session as DBSession
from .config import SECRET_KEY
from .models import Session, User

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return base64.urlsafe_b64encode(salt + digest).decode()

def verify_password(password: str, encoded: str) -> bool:
    try:
        raw = base64.urlsafe_b64decode(encoded.encode())
        return hmac.compare_digest(hashlib.scrypt(password.encode(), salt=raw[:16], n=2**14, r=8, p=1), raw[16:])
    except (ValueError, TypeError):
        return False

def create_session(db: DBSession, user: User) -> tuple[str, str]:
    token = secrets.token_urlsafe(32); csrf = secrets.token_urlsafe(24)
    db.add(Session(token_hash=session_token_hash(token), user_id=user.id, csrf_token=csrf, expires_at=datetime.now(timezone.utc)+timedelta(days=7)))
    db.commit(); return token, csrf

def session_token_hash(token: str) -> str:
    return hmac.new(SECRET_KEY.encode(), token.encode(), hashlib.sha256).hexdigest()

def revoke_user_sessions(db: DBSession, user_id: int) -> None:
    db.execute(delete(Session).where(Session.user_id == user_id))

def client_ip(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    try:
        trusted_peer = ipaddress.ip_address(peer).is_loopback
    except ValueError:
        trusted_peer = False
    if trusted_peer:
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        try:
            return str(ipaddress.ip_address(forwarded)) if forwarded else peer
        except ValueError:
            pass
    return peer

def current_user(request: Request, db: DBSession) -> User:
    token = request.cookies.get("review_session")
    if not token: raise HTTPException(401, "需要登录")
    session = db.get(Session, session_token_hash(token))
    if not session:
        raise HTTPException(401, "登录已过期")
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc): raise HTTPException(401, "登录已过期")
    user = db.get(User, session.user_id)
    if not user or not user.active: raise HTTPException(401, "账号不可用")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and request.headers.get("X-CSRF-Token") != session.csrf_token:
        raise HTTPException(403, "CSRF 校验失败")
    return user

def require_developer(user: User) -> User:
    if user.role != "developer": raise HTTPException(403, "需要开发者权限")
    return user
