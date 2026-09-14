import argparse
import os

from sqlalchemy import delete, select

from .db import SessionLocal
from .models import Session, User
from .security import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage review-system users without exposing secrets on the command line")
    subparsers = parser.add_subparsers(dest="command", required=True)
    reset = subparsers.add_parser("reset-password")
    reset.add_argument("username")
    reset.add_argument("--password-env", default="REVIEW_ADMIN_PASSWORD")
    args = parser.parse_args()

    password = os.getenv(args.password_env)
    if not password or len(password) < 12:
        raise SystemExit(f"{args.password_env} must contain at least 12 characters")

    with SessionLocal() as database:
        user = database.scalar(select(User).where(User.username == args.username))
        if not user:
            raise SystemExit(f"unknown user: {args.username}")
        user.password_hash = hash_password(password)
        database.execute(delete(Session).where(Session.user_id == user.id))
        database.commit()
    print(f"Password reset and sessions revoked for {args.username}")


if __name__ == "__main__":
    main()
