import argparse
import os

from sqlalchemy import delete, select

from .config import PASSWORD_MIN_LENGTH
from .db import SessionLocal
from .models import Session, User
from .security import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage review-system users without exposing secrets on the command line")
    subparsers = parser.add_subparsers(dest="command", required=True)
    reset = subparsers.add_parser("reset-password")
    reset.add_argument("username")
    reset.add_argument("--password-env", default="REVIEW_ADMIN_PASSWORD")
    create = subparsers.add_parser("create-user")
    create.add_argument("username")
    create.add_argument("--role", choices=("collaborator", "developer"), default="collaborator")
    create.add_argument("--password-env", default="REVIEW_NEW_USER_PASSWORD")
    disable = subparsers.add_parser("disable-user")
    disable.add_argument("username")
    subparsers.add_parser("list-users")
    args = parser.parse_args()

    if args.command == "list-users":
        with SessionLocal() as database:
            for user in database.scalars(select(User).order_by(User.username)):
                print(f"{user.username}\t{user.role}\t{'active' if user.active else 'disabled'}")
        return

    if args.command == "disable-user":
        with SessionLocal() as database:
            user = database.scalar(select(User).where(User.username == args.username))
            if not user:
                raise SystemExit(f"unknown user: {args.username}")
            if user.role == "developer" and user.active:
                active_developers = database.scalars(select(User).where(User.role == "developer", User.active.is_(True))).all()
                if len(active_developers) <= 1:
                    raise SystemExit("cannot disable the last active developer")
            user.active = False
            database.execute(delete(Session).where(Session.user_id == user.id))
            database.commit()
        print(f"Disabled {args.username} and revoked sessions")
        return

    password = os.getenv(args.password_env)
    if not password or len(password) < PASSWORD_MIN_LENGTH:
        raise SystemExit(f"{args.password_env} must contain at least {PASSWORD_MIN_LENGTH} characters")

    with SessionLocal() as database:
        if args.command == "create-user":
            if database.scalar(select(User).where(User.username == args.username)):
                raise SystemExit(f"user already exists: {args.username}")
            database.add(User(username=args.username, password_hash=hash_password(password), role=args.role))
            database.commit()
            print(f"Created {args.role} user {args.username}")
            return
        user = database.scalar(select(User).where(User.username == args.username))
        if not user:
            raise SystemExit(f"unknown user: {args.username}")
        user.password_hash = hash_password(password)
        database.execute(delete(Session).where(Session.user_id == user.id))
        database.commit()
    print(f"Password reset and sessions revoked for {args.username}")


if __name__ == "__main__":
    main()
