import base64
import json
from datetime import datetime, timezone
from typing import Any, TypeVar, Generic
from uuid import UUID
from pydantic import BaseModel
from sqlalchemy import or_, and_
from sqlalchemy.orm import Query

T = TypeVar("T")


def encode_cursor(created_at: datetime, entity_id: UUID | str) -> str:
    """Encodes created_at timestamp and entity ID into an opaque base64 cursor token."""
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    payload = {
        "t": created_at.isoformat(),
        "id": str(entity_id),
    }
    raw_json = json.dumps(payload)
    return base64.urlsafe_b64encode(raw_json.encode("utf-8")).decode("utf-8")


def decode_cursor(cursor_token: str | None) -> tuple[datetime, UUID] | None:
    """Decodes an opaque base64 cursor token into (created_at, entity_id). Returns None on invalid format."""
    if not cursor_token:
        return None
    try:
        raw_json = base64.urlsafe_b64decode(cursor_token.encode("utf-8")).decode("utf-8")
        data = json.loads(raw_json)
        dt = datetime.fromisoformat(data["t"])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt, UUID(data["id"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def paginate_keyset(
    query: Query,
    model: Any,
    cursor: str | None = None,
    limit: int = 50,
) -> tuple[list[Any], str | None, bool]:
    """
    Applies B-Tree keyset cursor pagination on (model.created_at DESC, model.id DESC).
    
    Complexity Contract:
      - O(log N + L) execution time via direct composite index seek.
      - Zero offset-scanning page drift under concurrent inserts.
      
    Returns:
      (items, next_cursor, has_next_page)
    """
    decoded = decode_cursor(cursor)
    if decoded is not None:
        cursor_dt, cursor_id = decoded
        # WHERE (created_at < :t) OR (created_at == :t AND id < :id)
        query = query.filter(
            or_(
                model.created_at < cursor_dt,
                and_(model.created_at == cursor_dt, model.id < cursor_id),
            )
        )

    # Order strictly by (created_at DESC, id DESC) for deterministic keyset traversal
    query = query.order_by(model.created_at.desc(), model.id.desc())

    # Fetch limit + 1 to detect if a next page exists without a separate COUNT(*) query
    items = query.limit(limit + 1).all()
    has_next = len(items) > limit
    page_items = items[:limit]

    next_cursor = None
    if has_next and page_items:
        last_item = page_items[-1]
        next_cursor = encode_cursor(last_item.created_at, last_item.id)

    return page_items, next_cursor, has_next


class CursorPage(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None
    has_next_page: bool = False
    limit: int = 50
