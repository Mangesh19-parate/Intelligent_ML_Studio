import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlalchemy.orm import Session
from app.models.project import Project
from app.models.dataset import Dataset
from app.models.user import User
from app.core.pagination import encode_cursor, decode_cursor, paginate_keyset
from app.services.workspace_analytics_service import derive_pipeline_stages_batch, derive_pipeline_stage
from app.repositories.project_repository import ProjectRepository


def test_cursor_encoding_and_decoding():
    now = datetime.now(timezone.utc)
    uid = uuid4()
    cursor = encode_cursor(now, uid)
    assert isinstance(cursor, str)

    decoded_dt, decoded_id = decode_cursor(cursor)
    assert decoded_id == uid
    # Compare timestamps within microsecond accuracy
    assert abs((decoded_dt - now).total_seconds()) < 0.001


def test_cursor_decoding_invalid_tokens():
    assert decode_cursor(None) is None
    assert decode_cursor("") is None
    assert decode_cursor("invalid_base64_???") is None
    assert decode_cursor("eyJpZCI6ICIxMjMifQ==") is None  # Missing 't' key


def test_keyset_pagination_mechanics(db_session: Session):
    owner_id = uuid4()
    base_time = datetime.now(timezone.utc)

    # Insert 15 projects with distinct descending timestamps
    projects = []
    for i in range(15):
        p = Project(
            id=uuid4(),
            owner_id=owner_id,
            project_name=f"Project_{i:02d}",
            created_at=base_time - timedelta(minutes=i),
            pipeline_stage="DATA",
        )
        db_session.add(p)
        projects.append(p)
    db_session.commit()

    repo = ProjectRepository(db_session)

    # Fetch page 1 (limit 5)
    page1, next_cursor1, has_next1 = repo.get_by_owner_keyset(owner_id=owner_id, cursor=None, limit=5)
    assert len(page1) == 5
    assert has_next1 is True
    assert next_cursor1 is not None
    assert [p.project_name for p in page1] == [f"Project_{i:02d}" for i in range(5)]

    # Fetch page 2 (limit 5) using next_cursor1
    page2, next_cursor2, has_next2 = repo.get_by_owner_keyset(owner_id=owner_id, cursor=next_cursor1, limit=5)
    assert len(page2) == 5
    assert has_next2 is True
    assert next_cursor2 is not None
    assert [p.project_name for p in page2] == [f"Project_{i:02d}" for i in range(5, 10)]

    # Fetch page 3 (limit 5) using next_cursor2
    page3, next_cursor3, has_next3 = repo.get_by_owner_keyset(owner_id=owner_id, cursor=next_cursor2, limit=5)
    assert len(page3) == 5
    assert has_next3 is False
    assert next_cursor3 is None
    assert [p.project_name for p in page3] == [f"Project_{i:02d}" for i in range(10, 15)]


def test_derive_pipeline_stages_batch_empty():
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        res = derive_pipeline_stages_batch([], db)
        assert res == {}
    finally:
        db.close()
