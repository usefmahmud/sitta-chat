"""Presence: who is online, announced only to people who share a room.

Presence is derived from the connection hub (a user is online while at least
one socket is open) and persisted on disconnect so ``last_seen`` survives a
restart. Nothing is stored per frame — the sprint risk table asked for that.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Conversation, ConversationMember, User
from .hub import hub


def audience_ids(db: Session, user_id: str) -> list[str]:
    """Ids of the people who share at least one conversation with ``user_id``."""
    mine = select(ConversationMember.conversation_id).where(
        ConversationMember.user_id == user_id
    )
    rows = db.scalars(
        select(ConversationMember.user_id)
        .join(Conversation, Conversation.id == ConversationMember.conversation_id)
        .where(
            ConversationMember.conversation_id.in_(mine),
            ConversationMember.user_id != user_id,
        )
        .distinct()
    ).all()
    return list(rows)


def shares_conversation(db: Session, user_a: str, user_b: str) -> bool:
    return user_b in set(audience_ids(db, user_a))


def frame(user_id: str, status: str, last_seen: datetime | None) -> dict[str, str | None]:
    return {
        "type": "presence",
        "user_id": user_id,
        "status": status,
        "last_seen": last_seen.isoformat() if last_seen else None,
    }


def touch_last_seen(db: Session, user_id: str) -> datetime:
    """Persist "seen now" with one-second resolution and return it."""
    seen = datetime.now(timezone.utc).replace(microsecond=0)
    user = db.get(User, user_id)
    if user is not None:
        user.last_seen_at = seen
        db.commit()
    return seen


async def announce_online(user_id: str, audience: list[str]) -> None:
    """Call only for the user's *first* socket."""
    now = datetime.now(timezone.utc)
    await hub.broadcast(audience, frame(user_id, "online", now))


async def announce_offline(user_id: str, audience: list[str], last_seen: datetime) -> None:
    """Call only after the user's *last* socket has been removed."""
    await hub.broadcast(audience, frame(user_id, "offline", last_seen))
