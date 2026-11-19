# chat-api

FastAPI + WebSocket + SQLite backend for sitta-chat.

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
curl -s localhost:8000/api/health
pytest
```

Configuration comes from the environment with the `CHAT_` prefix; see
`.env.example`. The database defaults to `./data/chat.db` (WAL mode).

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/health` | GET | liveness + database check |
