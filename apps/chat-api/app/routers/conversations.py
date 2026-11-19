"""1:1 conversations: create (idempotent), list, fetch."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import Conversation, User
from ..schemas import ConversationCreate, ConversationOut, UserOut
from ..services import conversations as service

router = APIRouter(prefix="/conversations", tags=["conversations"])


def to_out(conversation: Conversation) -> ConversationOut:
    return ConversationOut(
        id=conversation.id,
        type=conversation.type,
        created_at=conversation.created_at,
        participants=[UserOut.model_validate(u) for u in conversation.participants()],
    )


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationOut:
    """Create the 1:1 thread with a peer.

    201 when the thread is new, 200 with the existing thread when the same pair
    already has one — a double click never creates a duplicate.
    """
    if payload.peer_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cannot start a conversation with yourself",
        )

    peer = db.get(User, payload.peer_id)
    if peer is None or not peer.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="user not found"
        )

    conversation, created = service.create_direct(db, current_user, peer)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return to_out(conversation)


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ConversationOut]:
    return [to_out(c) for c in service.list_for_user(db, current_user.id)]


@router.get("/{conversation_id}", response_model=ConversationOut)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationOut:
    conversation = service.get_for_user(db, conversation_id, current_user.id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="conversation not found"
        )
    return to_out(conversation)
