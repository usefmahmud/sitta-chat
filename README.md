# sitta-chat

A complete chat application, built ticket by ticket by a crew of AI agents.

## Structure

```
apps/
  chat-api/   FastAPI + WebSockets + SQLite  (auth, conversations, messages, presence)
  chat-web/   React + Vite + Tailwind        (RTL Arabic UI)
docs/
  sprint-1.md      goals, tickets and acceptance criteria
  architecture.md  runtime shape and data model
```

## Workflow

`main ← staging ← dev ← feat/CHAT-N-slug`

One ticket, one branch, one small PR. Commit messages are validated by
[commitlint](commitlint.config.js) locally and in CI.

## Local development

```bash
# api
cd apps/chat-api && python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# web
cd apps/chat-web && npm install && npm run dev
```

## The crew

| Agent | Area |
|---|---|
| Hakim | Coordination, review gates |
| Maryam | Specs, acceptance criteria, sprint board |
| Omar | API + Web (implementation) |
| Salim | Research, protocol comparison, verification |
| Yassin | CI, containers, deploy |
| Layla | UI copy, docs, onboarding |

Licence: MIT
