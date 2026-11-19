"""The WebSocket entry point: ``/ws?token=<access_token>``."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from ..db import SessionLocal
from ..models import User
from ..realtime.hub import hub
from ..security import TokenError, decode_access_token
from ..services import conversations as conversation_service

router = APIRouter(tags=["realtime"])

UNAUTHORIZED_CLOSE_CODE = 4401


def _user_from_token(token: str | None) -> User | None:
    if not token:
        return None
    try:
        user_id = decode_access_token(token)
    except TokenError:
        return None

    with SessionLocal() as db:
        user = db.get(User, user_id)
        if user is None or not user.is_active:
            return None
        return user


def _conversation_ids(user_id: str) -> list[str]:
    with SessionLocal() as db:
        return [c.id for c in conversation_service.list_for_user(db, user_id)]


async def _error(websocket: WebSocket, code: str, detail: str) -> None:
    await websocket.send_json({"type": "error", "code": code, "detail": detail})


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str | None = Query(default=None),
) -> None:
    await websocket.accept()

    user = await run_in_threadpool(_user_from_token, token)
    if user is None:
        # Accept first so the client receives a real close code instead of an
        # opaque HTTP 403 during the handshake.
        await websocket.close(code=UNAUTHORIZED_CLOSE_CODE)
        return

    conversations = await run_in_threadpool(_conversation_ids, user.id)
    await hub.add(user.id, websocket)
    await websocket.send_json(
        {
            "type": "connection.ready",
            "user_id": user.id,
            "conversations": conversations,
        }
    )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload: Any = json.loads(raw)
            except json.JSONDecodeError:
                await _error(websocket, "bad_frame", "frame is not valid json")
                continue

            event_type = payload.get("type") if isinstance(payload, dict) else None
            if event_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            await _error(
                websocket,
                "unknown_event",
                f"unsupported event type: {event_type!r}",
            )
    except WebSocketDisconnect:
        pass
    finally:
        await hub.remove(user.id, websocket)
