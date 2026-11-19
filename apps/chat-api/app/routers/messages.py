"""Messages: send (idempotent) and read a thread with a keyset cursor."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import MessageCreate, MessageOut, MessagePage
from ..services import conversations as conversation_service
from ..services import messages as message_service

router = APIRouter(prefix="/conversations", tags=["messages"])

DEFAULT_PAGE_SIZE = 30
MAX_PAGE_SIZE = 100


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
)
def send_message(
    conversation_id: str,
    payload: MessageCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageOut:
    """201 for a new message, 200 when ``client_msg_id`` was already stored.

    Non-members get 404 — the room must not even be confirmed to exist.
    """
    if (
        conversation_service.get_for_user(db, conversation_id, current_user.id)
        is None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="conversation not found"
        )

    try:
        message, created = message_service.send_message(
            db,
            conversation_id=conversation_id,
            sender_id=current_user.id,
            body=payload.body.strip(),
            client_msg_id=payload.client_msg_id,
        )
    except message_service.MessageNotSaved as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="message could not be stored, retry",
        ) from exc

    response.status_code = (
        status.HTTP_201_CREATED if created else status.HTTP_200_OK
    )
    return MessageOut.model_validate(message)


@router.get("/{conversation_id}/messages", response_model=MessagePage)
def list_messages(
    conversation_id: str,
    before_seq: int | None = Query(default=None, ge=0),
    after_seq: int | None = Query(default=None, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessagePage:
    if (
        conversation_service.get_for_user(db, conversation_id, current_user.id)
        is None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="conversation not found"
        )

    messages, next_before_seq, has_more = message_service.page(
        db,
        conversation_id,
        before_seq=before_seq,
        after_seq=after_seq,
        limit=limit,
    )
    return MessagePage(
        items=[MessageOut.model_validate(m) for m in messages],
        next_before_seq=next_before_seq,
        has_more=has_more,
    )
