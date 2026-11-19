"""In-process registry of open WebSockets, keyed by user id.

One process, one hub (Sprint 1 runs a single uvicorn worker — see the sprint
risk table). A user may hold several sockets (phone + laptop); every socket is
kept and every one receives the same frames. Broadcasting skips the sender.

REST handlers are synchronous and run in a worker thread, so ``publish`` hops
back onto the application event loop with ``run_coroutine_threadsafe`` and waits
briefly for delivery. That keeps ordering deterministic in tests and keeps the
"emit after commit" rule visible in one place.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from starlette.websockets import WebSocket

logger = logging.getLogger(__name__)

PUBLISH_TIMEOUT_SECONDS = 2.0


class ConnectionHub:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    # -- lifecycle ---------------------------------------------------------
    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Remember the loop the app is running on (called from lifespan)."""
        self._loop = loop

    def reset(self) -> None:
        self._connections.clear()

    # -- registry ----------------------------------------------------------
    async def add(self, user_id: str, websocket: WebSocket) -> None:
        self._connections.setdefault(user_id, set()).add(websocket)

    async def remove(self, user_id: str, websocket: WebSocket) -> None:
        sockets = self._connections.get(user_id)
        if not sockets:
            return
        sockets.discard(websocket)
        if not sockets:
            self._connections.pop(user_id, None)

    def count(self, user_id: str) -> int:
        return len(self._connections.get(user_id, ()))

    def online_users(self) -> list[str]:
        return sorted(self._connections)

    # -- delivery ----------------------------------------------------------
    async def send_to_user(self, user_id: str, payload: dict[str, Any]) -> None:
        for websocket in list(self._connections.get(user_id, ())):
            try:
                await websocket.send_json(payload)
            except Exception:  # closed while we were writing to it
                await self.remove(user_id, websocket)

    async def broadcast(
        self, user_ids: list[str], payload: dict[str, Any]
    ) -> None:
        for user_id in user_ids:
            await self.send_to_user(user_id, payload)

    def publish(
        self,
        user_ids: list[str],
        payload: dict[str, Any],
        timeout: float = PUBLISH_TIMEOUT_SECONDS,
    ) -> None:
        """Fan a committed event out from synchronous code.

        Called *after* the database commit, so a failed write produces no
        frame. If nobody is connected this is a no-op.
        """
        if not user_ids:
            return

        loop = self._loop
        if loop is None or loop.is_closed():
            return

        # Already on the loop thread: schedule instead of deadlocking on
        # ``future.result()``.
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None

        if running is loop:
            loop.create_task(self.broadcast(user_ids, payload))
            return

        try:
            future = asyncio.run_coroutine_threadsafe(
                self.broadcast(user_ids, payload), loop
            )
        except RuntimeError:  # loop shut down between the check and the call
            return

        try:
            future.result(timeout=timeout)
        except Exception:  # pragma: no cover - slow consumer or closing socket
            future.cancel()
            logger.warning("websocket broadcast timed out for %s", user_ids)


hub = ConnectionHub()
