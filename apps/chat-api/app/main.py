"""FastAPI application factory."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import init_db
from .realtime.hub import hub
from .routers import auth, conversations, health, messages, presence, ws


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # REST handlers broadcast from worker threads, so the hub needs the loop.
    hub.bind_loop(asyncio.get_running_loop())
    init_db()
    yield
    hub.reset()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(conversations.router, prefix="/api")
    app.include_router(messages.router, prefix="/api")
    app.include_router(presence.router, prefix="/api")
    # The socket lives at /ws, outside the /api prefix.
    app.include_router(ws.router)
    return app


app = create_app()
