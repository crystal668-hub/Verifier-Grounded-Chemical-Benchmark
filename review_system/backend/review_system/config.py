from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.getenv("REVIEW_DATA_DIR", ROOT / "review_system" / "data"))
DATABASE_URL = os.getenv("REVIEW_DATABASE_URL", f"sqlite:///{DATA_DIR / 'review.db'}")
ENVIRONMENT = os.getenv("REVIEW_ENVIRONMENT", "development")
SECRET_KEY = os.getenv("REVIEW_SECRET_KEY", "dev-only-change-me")
ADMIN_USER = os.getenv("REVIEW_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("REVIEW_ADMIN_PASSWORD")
COOKIE_SECURE = os.getenv("REVIEW_COOKIE_SECURE", "false").lower() in {"1", "true", "yes"}
AUTO_CREATE_DB = os.getenv("REVIEW_AUTO_CREATE_DB", "true").lower() in {"1", "true", "yes"}
LOGIN_FAILURE_LIMIT = int(os.getenv("REVIEW_LOGIN_FAILURE_LIMIT", "5"))
LOGIN_WINDOW_MINUTES = int(os.getenv("REVIEW_LOGIN_WINDOW_MINUTES", "15"))
PASSWORD_MIN_LENGTH = 6
ALLOWED_ORIGINS = [item.strip() for item in os.getenv("REVIEW_ALLOWED_ORIGINS", "http://localhost:5173").split(",") if item.strip()]
SOURCE_ROOT = Path(os.getenv("REVIEW_SOURCE_ROOT", ROOT / "src" / "verifier_grounded_benchmark"))
MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024


def validate_production_config(*, database_is_empty: bool) -> None:
    if ENVIRONMENT != "production":
        if database_is_empty and (not ADMIN_PASSWORD or len(ADMIN_PASSWORD) < PASSWORD_MIN_LENGTH):
            raise RuntimeError(f"REVIEW_ADMIN_PASSWORD must contain at least {PASSWORD_MIN_LENGTH} characters")
        return
    if len(SECRET_KEY.encode()) < 32 or SECRET_KEY == "dev-only-change-me":
        raise RuntimeError("production REVIEW_SECRET_KEY must contain at least 32 bytes")
    if not COOKIE_SECURE:
        raise RuntimeError("production requires REVIEW_COOKIE_SECURE=true")
    if database_is_empty and (not ADMIN_PASSWORD or len(ADMIN_PASSWORD) < PASSWORD_MIN_LENGTH):
        raise RuntimeError(f"production REVIEW_ADMIN_PASSWORD must contain at least {PASSWORD_MIN_LENGTH} characters")
