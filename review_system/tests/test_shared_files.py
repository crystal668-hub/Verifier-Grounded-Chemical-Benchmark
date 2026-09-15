from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session as DBSession

from review_system.db import Base
from review_system.main import shared_files
from review_system.models import SharedFile, User


def test_shared_file_list_includes_utc_upload_time_in_newest_first_order():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    database = DBSession(engine, expire_on_commit=False)
    owner = User(username="uploader", password_hash="hash", role="collaborator")
    database.add(owner)
    database.flush()
    database.add_all([
        SharedFile(name="older.md", media_type="text/markdown", size=10, sha256="a" * 64, storage_path="older.md", owner_id=owner.id, created_at=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)),
        SharedFile(name="newer.md", media_type="text/markdown", size=10, sha256="b" * 64, storage_path="newer.md", owner_id=owner.id, created_at=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)),
    ])
    database.commit()

    try:
        result = shared_files(database, owner)

        assert [item["name"] for item in result] == ["newer.md", "older.md"]
        assert [item["created_at"] for item in result] == [
            "2025-01-01T12:00:00+00:00",
            "2025-01-01T10:00:00+00:00",
        ]
    finally:
        database.close()
        engine.dispose()
