"""``GET /api/presence?ids=a,b`` — presence, scoped to people I share a room with."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import User
from ..realtime.hub import hub
from ..realtime.presence import audience_ids

router = APIRouter(tags=["presence"])

MAX_IDS = 100


class PresenceEntry(BaseModel):
    user_id: str
    status: str
    last_seen: str | None = None


class PresenceResponse(BaseModel):
    users: list[PresenceEntry]


@router.get("/presence", response_model=PresenceResponse)
def read_presence(
    ids: str = Query(default="", description="comma separated user ids"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PresenceResponse:
    """Unknown ids and ids outside my rooms are omitted, never reported."""
    requested = [raw.strip() for raw in ids.split(",") if raw.strip()][:MAX_IDS]
    allowed = set(audience_ids(db, current_user.id))

    entries: list[PresenceEntry] = []
    for user_id in requested:
        if user_id not in allowed:
            continue
        user = db.get(User, user_id)
        if user is None or not user.is_active:
            continue
        entries.append(
            PresenceEntry(
                user_id=user_id,
                status="online" if hub.count(user_id) else "offline",
                last_seen=(
                    user.last_seen_at.isoformat() if user.last_seen_at else None
                ),
            )
        )

    return PresenceResponse(users=entries)
