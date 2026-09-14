from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as DBSession

from review_system.db import Base
from review_system.main import comments, delete_comment
from review_system.models import Comment, User


def _database_with_comments():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    database = DBSession(engine, expire_on_commit=False)
    owner = User(username="owner", password_hash="hash", role="collaborator")
    other = User(username="other", password_hash="hash", role="collaborator")
    developer = User(username="developer", password_hash="hash", role="developer")
    database.add_all([owner, other, developer])
    database.flush()
    root = Comment(target_type="task", target_id="task-1", author_id=owner.id, body="root")
    database.add(root)
    database.flush()
    child = Comment(target_type="task", target_id="task-1", author_id=other.id, parent_id=root.id, body="reply")
    database.add(child)
    database.commit()
    return database, owner, other, developer, root, child


def test_comment_list_reports_delete_permission():
    database, owner, other, _developer, root, child = _database_with_comments()
    try:
        owner_view = {item["id"]: item for item in comments("task-1", database, owner)}
        assert owner_view[root.id]["can_delete"] is True
        assert owner_view[child.id]["can_delete"] is False

        other_view = {item["id"]: item for item in comments("task-1", database, other)}
        assert other_view[root.id]["can_delete"] is False
        assert other_view[child.id]["can_delete"] is True
    finally:
        database.close()


def test_only_author_or_developer_can_delete_comment():
    database, _owner, other, developer, root, child = _database_with_comments()
    try:
        with pytest.raises(HTTPException) as raised:
            delete_comment(root.id, database, other)
        assert raised.value.status_code == 403

        assert delete_comment(root.id, database, developer) == {"ok": True, "id": root.id}
        assert database.get(Comment, root.id) is None
        assert database.get(Comment, child.id).parent_id is None
    finally:
        database.close()
