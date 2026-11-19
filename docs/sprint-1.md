# Sprint 1 — sitta-chat

| | |
|---|---|
| **Board** | Atlas project `CHAT` — tickets `CHAT-1 … CHAT-13` |
| **Repo** | `github.com/usefmahmud/sitta-chat` (private) |
| **Ticket** | `CHAT-9` — Sprint 1 plan + acceptance criteria |
| **Owner of this document** | Maryam (PM) |
| **Plan state** | **Awaiting owner (Youssef) approval** — the 2-day commitment in §7 is a proposal, not a promise |
| **Branch** | `docs/CHAT-9-sprint-plan` → PR to `dev` |
| **Written** | 2026-11-19 UTC |

---

## 1. Sprint goal

Ship a **working one-to-one chat** — register, log in, open a conversation, send a message, and see it arrive on the other side in under half a second — in Arabic, right-to-left, on a phone.

Everything in Sprint 1 serves that single path; group chats, attachments, search and push notifications are explicitly out of scope.

**"Done" for the sprint means:** a fresh clone runs the stack with the documented command, two browsers sign in as two users, a message typed in one appears in the other without a refresh, the presence dot flips within 5 seconds of closing the tab, and `dev` is green in CI.

---

## 2. Tickets at a glance

13 tickets, 63 acceptance criteria, 8 owned by the single API/Web implementer (Omar) — see the capacity note in §7.

| ID | Title | Owner | Branch | ACs | Depends on |
|---|---|---|---|---|---|
| CHAT-1 | API skeleton: FastAPI + settings + SQLite + `/api/health` | omar | `feat/CHAT-1-api-skeleton` | 5 | — |
| CHAT-2 | Auth: register/login with JWT + pytest | omar | `feat/CHAT-2-jwt-auth` | 5 | CHAT-1 |
| CHAT-3 | Conversations: model + list/create 1:1 + tests | omar | `feat/CHAT-3-conversations` | 5 | CHAT-2 |
| CHAT-4 | Messages: send + paginated list + tests | omar | `feat/CHAT-4-message-pagination` | 5 | CHAT-3 |
| CHAT-5 | Realtime: WebSocket broadcast + tests | omar | `feat/CHAT-5-websocket-broadcast` | 6 | CHAT-4 |
| CHAT-6 | Presence: online/offline over WebSocket + tests | omar | `feat/CHAT-6-presence` | 4 | CHAT-5 |
| CHAT-7 | Web: auth screens + API client (RTL) | omar | `feat/CHAT-7-auth-screens` | 5 | CHAT-2, CHAT-13 |
| CHAT-8 | Web: chat list + thread + composer (RTL) | omar | `feat/CHAT-8-chat-ui` | 6 | CHAT-5, CHAT-7 |
| CHAT-9 | Sprint 1 plan + acceptance criteria (this file) | maryam | `docs/CHAT-9-sprint-plan` | 4 | — |
| CHAT-10 | CI: commitlint + pytest + web build on PRs | yassin | `ci/CHAT-10-pipeline` | 4 | CHAT-1 |
| CHAT-11 | Docker: compose for api + web with healthchecks | yassin | `chore/CHAT-11-docker` | 5 | CHAT-1, CHAT-10 |
| CHAT-12 | Research: WS vs SSE + pagination strategy | salim | `docs/CHAT-12-realtime-research` | 4 | — |
| CHAT-13 | Copy: Arabic UI text, empty states, error messages | layla | `docs/CHAT-13-ui-copy` | 5 | — |

> **Drift note:** the CHAT-9 description on the board still says *"9 tickets"*. The project actually has **13** (`CHAT-1 … CHAT-13`, verified against the board on 2026-11-19). This plan covers all 13; the ticket description should be corrected on `review`.

---

## 3. Acceptance criteria and evidence

Shape of every ticket below: numbered criteria that a reviewer can check with a command, plus the definition of done for a ticket (§5). Every criterion is written to **fail before** the branch merges and **pass after** — a criterion nobody can run is not a criterion.

### CHAT-1 · API skeleton — FastAPI + settings + SQLite + `/api/health`

**Owner:** omar · **Branch:** `feat/CHAT-1-api-skeleton` · **Depends on:** — · **Size:** ~2h · **Deliverable:** `apps/chat-api/`
**Merged:** 2026-11-19, PR #1 (`dev@7397871`). Configuration names below are the ones now in `app/config.py` — every later ticket uses them.

- **AC-01** — The app boots with `uvicorn app.main:app --port 8000` and `GET /api/health` answers **200** with `{"status":"ok","service":"sitta-chat-api","version":"0.1.0","environment":"development","database":"ok"}`.
  `cd apps/chat-api && uvicorn app.main:app --port 8000 & sleep 2 && curl -s localhost:8000/api/health | jq -e '.status=="ok" and .database=="ok"'` → exit 0
- **AC-02** — Health degrades honestly: with an unusable `CHAT_DATABASE_URL` the same endpoint returns **503** and `"database":"error"` instead of a green lie.
  `CHAT_DATABASE_URL=sqlite:////proc/nope.db pytest -q tests/test_health.py` → green
- **AC-03** — Configuration comes from the environment through pydantic-settings with the `CHAT_` prefix (`CHAT_DATABASE_URL`, `CHAT_SECRET_KEY`, `CHAT_ACCESS_TOKEN_TTL_MINUTES`, `CHAT_CORS_ORIGINS`), `.env.example` lists every key, and **no secret has a hardcoded default** — the app must refuse to start outside `development` with the placeholder key.
  `CHAT_ENVIRONMENT=production python -c "import app.main"` → exits non-zero with a clear message; `grep -rn "change-me\|dev-only" apps/chat-api/app` → 0 matches
- **AC-04** — SQLite is opened in WAL mode with `foreign_keys=ON` **and `busy_timeout=5000`**, behind one `get_db` dependency; a test asserts all three pragmas (this is the mitigation for R1, so it is not optional).
  `sqlite3 apps/chat-api/data/chat.db "PRAGMA journal_mode; PRAGMA busy_timeout; PRAGMA foreign_keys;"` → `wal` / `5000` / `1`
- **AC-05** — Repo hygiene: pinned `requirements.txt`, `pythonpath = .` in `pytest.ini`, `data/`, `*.db`, `.env` ignored, and `apps/chat-api/README.md` documents the exact run command.
  `git status --porcelain | grep -c '\.db$\|\.env$'` → `0` and `cd apps/chat-api && python -m pytest -q` → exit 0

**Merged state:** AC-01 ✅, AC-05 ✅. Gaps to fold into the next API branch (3–10 lines, no new ticket): AC-02 (the handler lets the exception bubble to a 500), AC-03 (`secret_key` still defaults to `dev-only-insecure-secret-change-me`), AC-04 (`busy_timeout` pragma is missing — the one line that stops R1's `database is locked`). Recommended owner: omar, inside the CHAT-2 branch.

### CHAT-2 · Auth — register / login with JWT + pytest

**Owner:** omar · **Branch:** `feat/CHAT-2-jwt-auth` · **Depends on:** CHAT-1 · **Size:** ~3h · **Deliverable:** `app/routers/auth.py`, `app/security.py`, `app/deps.py`, `tests/test_auth.py`
**Contract decided with CHAT-1:** one access token (HS256, `CHAT_ACCESS_TOKEN_TTL_MINUTES`, default 60), **no refresh token in Sprint 1** — see §8. Register returns the token too, so the client never needs a second round trip.

- **AC-01** — `POST /api/auth/register` with `{email, password, display_name}` returns **201** with `{access_token, expires_in, user:{id,email,display_name}}`; email is trimmed and lower-cased before the uniqueness check.
  `curl -s -XPOST localhost:8000/api/auth/register -H 'content-type: application/json' -d '{"email":"A@x.io","password":"secret123","display_name":"A"}' | jq -r .user.email` → `a@x.io`
- **AC-02** — Passwords are stored only as bcrypt (`$2b$`), the plaintext appears in no log line and no fixture, and a password over 72 bytes is rejected instead of silently truncated.
  `sqlite3 data/chat.db "select substr(password_hash,1,4) from users limit 1;"` → `$2b$`; `grep -rn "secret123" apps/chat-api/app` → 0
- **AC-03** — Duplicate email → **409** (including the lost race against a concurrent signup, via `IntegrityError`); password shorter than 8 chars or malformed email → **422** with a field-level error body.
  `pytest -q tests/test_auth.py -k "duplicate or validation"` → green
- **AC-04** — `POST /api/auth/login` → **200** with the same token envelope; a wrong password and an unknown email return the **same** generic 401 (no user enumeration).
  `pytest -q tests/test_auth.py -k "login or enumeration"` → green
- **AC-05** — `GET /api/me` with `Authorization: Bearer …` → **200**; missing, expired or tampered token → **401**. `deps.get_current_user` is the single reusable dependency that CHAT-3…CHAT-6 import unchanged.
  `pytest -q tests/test_auth.py` → ≥ 8 tests, exit 0

**State:** merged, PR #4 (`dev@08083c6`, 13 auth tests). AC-01/02/03/05 satisfied as delivered. **The three CHAT-1 gaps were not carried over** — verified on `08083c6`: `secret_key` still defaults to `dev-only-insecure-secret-change-me`, `db.py` sets WAL + `foreign_keys` but no `busy_timeout`, and health still has no 503 path. They must land before CHAT-4's concurrency test, otherwise R1 is unmitigated.

### CHAT-3 · Conversations — model + list/create 1:1 + tests

**Owner:** omar · **Branch:** `feat/CHAT-3-conversations` · **Depends on:** CHAT-2 · **Size:** ~2.5h · **Deliverable:** `app/models/conversation.py`, `app/routers/conversations.py`, `tests/test_conversations.py`

- **AC-01** — `conversations(id, type, created_at, last_message_at)` and `conversation_members(conversation_id, user_id, joined_at, last_read_seq)` exist with FKs and `UNIQUE(conversation_id, user_id)`.
  `sqlite3 data/chat.db ".schema conversation_members"` → shows both FKs and the unique index
- **AC-02** — `POST /api/conversations {"peer_id": "…"}` → **201** with `{id, peer, created_at}`; posting the same pair again → **200** with the *same* id (1:1 creation is idempotent, no duplicate rooms).
  `pytest -q tests/test_conversations.py -k idempotent` → green
- **AC-03** — `GET /api/conversations` returns only rooms I am a member of, ordered by `last_message_at DESC` (empty rooms last), each with the peer summary and a last-message preview.
  `pytest -q tests/test_conversations.py -k ordering` → green
- **AC-04** — A room I am not a member of answers **404** (not 403) on read — non-membership must not leak that the room exists.
  `pytest -q tests/test_conversations.py -k "not_member or 404"` → green
- **AC-05** — Creating a conversation with yourself → **422**; with an unknown peer id → **404**.
  `pytest -q tests/test_conversations.py` → exit 0

### CHAT-4 · Messages — send + paginated list + tests

**Owner:** omar · **Branch:** `feat/CHAT-4-message-pagination` · **Depends on:** CHAT-3 · **Size:** ~3h · **Deliverable:** `app/models/message.py`, `app/routers/messages.py`, `tests/test_messages.py`

- **AC-01** — `messages(id, conversation_id, sender_id, seq, body, client_msg_id, created_at)` with `UNIQUE(conversation_id, seq)` and `UNIQUE(sender_id, client_msg_id)`.
  `sqlite3 data/chat.db ".schema messages"` → both unique constraints present
- **AC-02** — `POST /api/conversations/{id}/messages {"body":"…","client_msg_id":"…"}` → **201** `{id, seq, created_at, sender_id}`; `seq` increments by exactly 1 per conversation and is assigned **inside the write transaction**. Re-posting the same `client_msg_id` returns the original message, not a duplicate.
  `pytest -q tests/test_messages.py -k "seq or idempotent"` → green
- **AC-03** — `GET /api/conversations/{id}/messages?before_seq=&limit=` returns a newest-first page (default 30, max 100) over a **keyset** cursor: walking 120 messages in pages of 30 yields every `seq` exactly once.
  `pytest -q tests/test_messages.py -k pagination` → asserts `sorted(seen) == list(range(1,121))`
- **AC-04** — Empty or whitespace-only body → **422**; body > 4000 chars → **422**; non-member → **404**.
  `pytest -q tests/test_messages.py -k "validation or member"` → green
- **AC-05** — A successful send bumps `conversations.last_message_at` **in the same transaction**, so CHAT-3's ordering reflects the new message immediately.
  `pytest -q tests/test_messages.py -k last_message_at` → green

### CHAT-5 · Realtime — WebSocket broadcast + tests

**Owner:** omar · **Branch:** `feat/CHAT-5-websocket-broadcast` · **Depends on:** CHAT-4 · **Size:** ~3.5h · **Deliverable:** `app/realtime/`, `tests/test_realtime.py`

- **AC-01** — `WS /ws?token=<access_token>` accepts a valid token; with an invalid or expired one the server closes with code **4401** before any subscription happens.
  `pytest -q tests/test_realtime.py -k "auth or 4401"` → green
- **AC-02** — On connect the socket is auto-subscribed to every conversation the user is a member of; the connection registry is keyed by `user_id` and holds N sockets per user.
  `pytest -q tests/test_realtime.py -k registry` → green
- **AC-03** — A message sent over REST arrives on every *other* member's socket as `{"type":"message.created","message":{…}}` within **500 ms**.
  `pytest -q tests/test_realtime.py -k broadcast` → green
- **AC-04** — A user who is not a member of the conversation receives **zero** frames for it (3-user test: 2 in, 1 out).
  `pytest -q tests/test_realtime.py -k isolation` → green
- **AC-05** — The event is emitted **after** the DB commit: a rolled-back transaction produces no frame (no ghost messages).
  `pytest -q tests/test_realtime.py -k "rollback or commit"` → green
- **AC-06** — Disconnecting removes the socket from the registry (count returns to 0); an unknown event type or malformed frame gets an error frame and the connection stays open.
  `pytest -q tests/test_realtime.py` → ≥ 6 tests, exit 0

### CHAT-6 · Presence — online/offline over WebSocket + tests

**Owner:** omar · **Branch:** `feat/CHAT-6-presence` · **Depends on:** CHAT-5 · **Size:** ~2h · **Deliverable:** `app/realtime/presence.py`, `tests/test_presence.py`

- **AC-01** — Connect and disconnect broadcast `{"type":"presence","user_id":…,"status":"online"|"offline","last_seen":…}` to users who share a conversation, and to nobody else.
  `pytest -q tests/test_presence.py -k broadcast` → green
- **AC-02** — `GET /api/presence?ids=a,b` answers only for ids that share a conversation with the caller; foreign ids are omitted rather than reported.
  `pytest -q tests/test_presence.py -k scope` → green
- **AC-03** — `users.last_seen_at` is persisted on disconnect with ≤ 5 s granularity.
  `sqlite3 data/chat.db "select last_seen_at from users limit 1;"` → an ISO-8601 timestamp
- **AC-04** — A user with two sockets stays `online` until the **last** one closes, and no offline/online flap is emitted in between.
  `pytest -q tests/test_presence.py` → exit 0

### CHAT-7 · Web — auth screens + API client (RTL)

**Owner:** omar · **Branch:** `feat/CHAT-7-auth-screens` · **Depends on:** CHAT-2 (API), CHAT-13 (keys) · **Size:** ~3.5h · **Deliverable:** `apps/chat-web/`

- **AC-01** — Vite + React + TypeScript + Tailwind are wired (`tailwind.config.js`, `postcss.config.js`, `npm run build`) and the production build exits 0.
  `cd apps/chat-web && npm ci && npm run build` → exit 0, `dist/index.html` exists
- **AC-02** — RTL is a global fact, not per-component styling: `<html lang="ar" dir="rtl">`, Arabic-capable font stack, and no physical left/right spacing utilities in `src/`.
  `grep -c 'dir="rtl"' apps/chat-web/index.html` → `1`; `grep -rnE '\b(ml|mr|pl|pr)-[0-9]' apps/chat-web/src | wc -l` → `0`
- **AC-03** — `/login` and `/register` render, validate (email shape, password ≥ 8), call the client and keep the access token **in memory only** (no `localStorage`/`sessionStorage` write) — a page reload returns to `/login`, which is the accepted Sprint 1 trade-off without refresh tokens.
  `grep -rn "localStorage\|sessionStorage" apps/chat-web/src | wc -l` → `0`
- **AC-04** — `src/lib/api.ts` takes `VITE_API_URL`, exposes typed errors, and on **401** clears the session and routes to `/login` (no retry loop against a dead token).
  a test in `src/lib/api.test.ts` covers the 401 → logout path and the network-error path
- **AC-05** — Every visible string resolves through `t()` against `src/i18n/ar.ts` and the key set matches `docs/copy-ar.md`; no literal Arabic or English prose in JSX.
  `cd apps/chat-web && npm run test:i18n` → key parity green; `grep -rnP '>\s*[A-Za-z\u0600-\u06FF]{2,}' src --include=*.tsx | wc -l` → `0`

### CHAT-8 · Web — chat list + thread + composer (RTL)

**Owner:** omar · **Branch:** `feat/CHAT-8-chat-ui` · **Depends on:** CHAT-5, CHAT-7 · **Size:** ~5h · **Deliverable:** `apps/chat-web/src/features/chat/`

- **AC-01** — The list renders `GET /api/conversations` with peer name, last-message preview, unread badge and Arabic relative time via `Intl.RelativeTimeFormat('ar')`.
  `grep -rn "RelativeTimeFormat" apps/chat-web/src | wc -l` ≥ 1, list screenshot in the PR
- **AC-02** — The thread loads the newest page on open and pages upward with `before_seq` on scroll, grouped by day, with **no duplicate React keys** (dedupe by `id`).
  browser console free of `Encountered two children with the same key` during a 120-message scroll test
- **AC-03** — The composer appends optimistically with `status: sending` → `sent` on 201 → `failed` + retry on error; Enter sends, Shift+Enter inserts a newline; the input is disabled while a send is in flight.
  manual script in the PR description (send, kill the API, send again, retry)
- **AC-04** — An incoming `message.created` for the open thread appends and auto-scrolls only when the user is within 120 px of the bottom; otherwise a "new messages" pill appears.
  `document.querySelector('#thread').scrollTop` check with two tabs, transcript in the PR
- **AC-05** — Reconnect is lossless: on close the socket retries with exponential backoff (1 s → 30 s), and on reopen the client fetches `after_seq=<last_seq>` so every message appears **exactly once**.
  kill the API for 10 s during a live session, restart → thread shows all messages, zero duplicates
- **AC-06** — Mobile RTL: at 360×800 there is no horizontal scroll (`document.documentElement.scrollWidth <= 360`), the composer sits above the keyboard, and bubbles align start/end by sender using logical properties.
  `await page.setViewportSize({width:360,height:800}); await page.evaluate(() => document.documentElement.scrollWidth)` → `<= 360`

### CHAT-9 · Sprint 1 plan + acceptance criteria (this file)

**Owner:** maryam · **Branch:** `docs/CHAT-9-sprint-plan` · **Depends on:** — · **Deliverable:** `docs/sprint-1.md`

- **AC-01** — The document lists all 13 tickets with owner, branch, dependencies and at least four numbered acceptance criteria each.
  `grep -c '^### CHAT-' docs/sprint-1.md` → `13`
- **AC-02** — Every criterion names a command or a browser assertion and the result that makes it pass; no criterion is "it works".
  `grep -c '^- \*\*AC-' docs/sprint-1.md` → `63`
- **AC-03** — The execution order section shows the blocking chain `CHAT-1 → 2 → 3 → 4 → 5 → 6` and the parallel tracks (10, 11, 12, 13) with no circular dependency.
  read §4 — dependency rows contain no ticket that depends on its own successor
- **AC-04** — The risk section covers SQLite write contention, message ordering, message loss on reconnect and RTL on mobile, each with likelihood, impact, mitigation and an owner — and names the single largest risk.
  `grep -c '^| R[0-9]' docs/sprint-1.md` → `6` (4 required + 2 project-level)

### CHAT-10 · CI — commitlint + pytest + web build on PRs

**Owner:** yassin · **Branch:** `ci/CHAT-10-pipeline` · **Depends on:** CHAT-1 · **Size:** ~1.5h · **Deliverable:** `.github/workflows/ci.yml`

- **AC-01** — Four jobs run on every PR to `dev`: `commitlint`, `api (pytest)`, `web (build)`, `branch name` — and they are the required checks in branch protection, so a red run blocks the merge button.
  `gh api repos/usefmahmud/sitta-chat/branches/dev/protection | jq -r '.required_status_checks.contexts[]'` → the four job names
- **AC-02** — commitlint validates the **whole PR range** (`base.sha..head.sha`), not just the tip: a PR whose second commit is `update stuff` fails the job.
  throwaway PR with that message → `commitlint` job red, then closed unmerged
- **AC-03** — The api job installs `apps/chat-api/requirements.txt` on Python 3.12 and runs `pytest -q`; the web job runs `npm ci && npm run build` on Node 22; both are cached and finish under 4 minutes.
  `gh run list --workflow=CI --limit 1 --json conclusion,durationMs` → `success`, `< 240000`
- **AC-04** — `dev` rejects direct pushes (`gh api .../protection | jq .enforce_admins` and `allow_force_pushes=false`), requires one approval and linear history.
  `gh api repos/usefmahmud/sitta-chat/branches/dev/protection | jq '.required_pull_request_reviews.required_approving_review_count'` → `1`

### CHAT-11 · Docker — compose for api + web with healthchecks

**Owner:** yassin · **Branch:** `chore/CHAT-11-docker` · **Depends on:** CHAT-1, CHAT-10 · **Size:** ~2h · **Deliverable:** `docker-compose.yml`, `apps/*/Dockerfile`

- **AC-01** — `docker compose up -d --build` from the repo root brings up `api` and `web` with no manual steps beyond copying `.env.example`.
  `docker compose up -d --build && docker compose ps --format '{{.Name}} {{.Status}}'` → two services listed
- **AC-02** — Both services report `healthy` within 60 s: the API healthcheck hits `/api/health`, the web healthcheck hits `/`.
  `sleep 60 && docker compose ps --format json | jq -r '.Health'` → `healthy` twice
- **AC-03** — The web image serves the SPA with history fallback (`try_files $uri /index.html`), and `VITE_API_URL` is injected at build time, so a deep link such as `/chat/123` reloads without a 404.
  `curl -s -o /dev/null -w '%{http_code}' localhost:3000/chat/123` → `200`
- **AC-04** — Data lives in the named volume `chat-data` and survives `docker compose down && docker compose up -d`; the DB file is never baked into an image.
  `docker compose down && docker compose up -d` then `docker compose exec api ls -l /data/chat.db` → same size/mtime as before
- **AC-05** — No secrets in the images: `.dockerignore` covers `.env*`, `node_modules`, `*.db`; `docker history --no-trunc` shows no token or key.
  `docker history --no-trunc sitta-chat/api:dev | grep -ci "secret\|token"` → `0`

### CHAT-12 · Research — WebSocket vs SSE + pagination strategy

**Owner:** salim · **Branch:** `docs/CHAT-12-realtime-research` · **Depends on:** — · **Size:** ~2h · **Deliverable:** `docs/research-realtime.md`

- **AC-01** — A comparison table of WebSocket, SSE and long-polling across bidirectionality, reconnect behaviour, proxy/CDN friendliness, auth, and operational cost — with at least five cited sources (links, not adjectives).
  `grep -c 'https://' docs/research-realtime.md` → `>= 5`
- **AC-02** — The pagination section compares offset/limit with keyset cursors and states which one CHAT-4 implements, with the reasoning and the failure mode of the rejected option.
  `grep -n "keyset\|offset" docs/research-realtime.md` → both discussed with a recommendation
- **AC-03** — There is one explicit recommendation (WS for this sprint) and a named fallback if a proxy turns out to break upgrades.
  `grep -c '^## Recommendation' docs/research-realtime.md` → `1`
- **AC-04** — Every claim carries its source next to it; no unsourced performance numbers.
  review: each numeric claim in the table has a link or is removed

### CHAT-13 · Copy — Arabic UI text, empty states, error messages

**Owner:** layla · **Branch:** `docs/CHAT-13-ui-copy` · **Depends on:** — · **Size:** ~3h · **Deliverable:** `docs/copy-ar.md`, `apps/chat-web/src/i18n/ar.ts`

- **AC-01** — `docs/copy-ar.md` groups keys by screen (`login.*`, `register.*`, `chat.*`, `thread.*`, `message.*`, `connection.*`, `common.*`), each key with its Arabic string and one line of context.
  `grep -cE '^\| `[a-z]+\.[a-z0-9_.]+`' docs/copy-ar.md` → `>= 40`
- **AC-02** — `apps/chat-web/src/i18n/ar.ts` exports the same key paths; a test asserts key parity in both directions and runs in CI.
  `cd apps/chat-web && npm run test:i18n` → parity green, 0 missing / 0 extra
- **AC-03** — Empty states (no conversations, no messages, no search results) and error states (network down, 401, 500) each have their own string — no generic "something went wrong" for all of them.
  `grep -cE 'empty\.|error\.' docs/copy-ar.md` → `>= 10`
- **AC-04** — Connection states `connecting` / `reconnecting` / `offline` have strings, and the reconnect string can carry a countdown placeholder.
  `grep -c 'connection\.' docs/copy-ar.md` → `>= 3`
- **AC-05** — Direction rules hold: no string mixes Arabic and Latin inside one sentence without a `bdi` plan, no leading/trailing spaces, Latin digits chosen consistently.
  `grep -nP '^\|.*\S\s+\|\s*$' docs/copy-ar.md` → 0 trailing-space cells

**State:** merged, PR #2 (`dev@7397871`). AC-01 verified against the real file: **114 key rows** (`grep -cE '^\| `[a-z]+\.[a-z0-9_.]+`'`) — well above the 40 threshold. AC-02 (`src/i18n/ar.ts` parity test) is still owed by CHAT-7, which consumes the key set.

---

## 4. Execution order and dependencies

Blocking chain (each arrow is a merge to `dev` before the next branch is cut):

```
CHAT-1 ──▶ CHAT-2 ──▶ CHAT-3 ──▶ CHAT-4 ──▶ CHAT-5 ──▶ CHAT-6
   │                        │                    │
   ├──▶ CHAT-10 ──▶ CHAT-11 │                    │
   │                        │                    ▼
   │                        └──▶ CHAT-7 ──▶ CHAT-8
   │                                   ▲
CHAT-13 ───────────────────────────────┘        CHAT-12 ──▶ (informs CHAT-5)
```

| Wave | Tickets | Runs when | Notes |
|---|---|---|---|
| **W0** — unblock | CHAT-1, CHAT-12, CHAT-13, CHAT-9 | immediately, in parallel | 1 is the gate for everything API; 12/13 need no code |
| **W1** — API chain | CHAT-2 → CHAT-3 → CHAT-4 → CHAT-5 → CHAT-6 | strictly sequential | each branch is cut from `dev` **after** the previous PR merges; do not stack branches |
| **W1** — infra track | CHAT-10 (after 1), CHAT-11 (after 10) | parallel to W1 chain | CI must exist before CHAT-2 lands, otherwise the first PR has no gate |
| **W2** — web track | CHAT-7 (after 2 + 13), CHAT-8 (after 5 + 7) | parallel to W1 chain once 2 merges | 7 can start against a stub API client; 8 needs real sockets |
| **W3** — close | CHAT-9 review, sprint DoD pass | after 8 and 6 merge | the demo in §1 is the acceptance test |

Rules of the road that come from these dependencies:

1. **One ticket, one branch, one PR to `dev`** — never `main`, never stacked branches.
2. A ticket starts only when its dependency is **merged** (not "almost done"), because the next branch is cut from `dev`.
3. `dev` must stay green: CHAT-10 lands before CHAT-2, so the first feature PR already has a gate.
4. CHAT-12's recommendation is read before CHAT-5 is implemented; if it argues for SSE, CHAT-5 is re-scoped **before** code is written, not after.

---

## 5. Definition of Done

**A ticket is done when** — all of these, in order:

- [ ] its branch is `type/CHAT-N-slug`, cut from an up-to-date `dev`;
- [ ] every commit matches `type(scope): subject` with an allow-listed scope (CI enforces it);
- [ ] every AC in §3 has been run and its real output pasted into the PR (not summarised);
- [ ] tests for the ticket pass locally and in CI;
- [ ] no `.env`, database file, token or key in the diff;
- [ ] the ticket is moved to `review` on Atlas with a comment naming the artifact path and the evidence command.

**The sprint is done when** — all of these:

- [ ] 13 tickets are `review` or `done` on the Atlas `CHAT` board;
- [ ] `dev` CI is green on the last commit: commitlint + pytest + web build + branch gate;
- [ ] the §1 demo works end to end from a fresh clone: register → login → conversation → send → live receive in a second tab → presence flips;
- [ ] `docker compose up` on a clean machine reproduces the same demo (CHAT-11);
- [ ] no secrets or data files tracked: `git ls-files | grep -cE '\.env$|\.db$'` → `0`;
- [ ] sprint report written to `~/ai-team/shared/reports/` with the AC table and the live evidence block.

---

## 6. Risks

| # | Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|---|
| R1 | **SQLite write contention** — concurrent sends (and the WS fan-out writing presence) hit `database is locked`, so messages fail or retry silently | High | High | WAL + `busy_timeout=5000` + short transactions that never span an `await`; single uvicorn worker in Sprint 1 (no `--workers`); presence writes batched on disconnect, not per frame; load test 20 concurrent senders in CHAT-4 | omar |
| R2 | **Message ordering** — `created_at` ties or clock skew reorder the thread; a duplicate `seq` under concurrent inserts corrupts pagination | Medium | High | `seq` assigned inside the write transaction, `UNIQUE(conversation_id, seq)`, clients sort by `seq` and never by timestamp; pagination test walks 120 messages and asserts no gap/duplicate | omar |
| R3 | **Message loss on reconnect** — the socket drops mid-send; the client either misses messages sent while offline or renders duplicates after retry | High | High | client keeps `last_seq`, refetches with `after_seq` on reopen, sends with `client_msg_id` so a retry is idempotent server-side; explicit CHAT-8/AC-05 test that kills the API for 10 s | omar |
| R4 | **RTL on mobile** — physical `ml/mr` utilities, fixed pixel widths and `direction: ltr` leaks produce mirrored layouts and horizontal scroll at 360 px | Medium | Medium | `dir="rtl"` on `<html>`, logical properties only (`ms/me/ps/pe`, `text-start`), no fixed widths, `scrollWidth <= 360` assertion in CHAT-8/AC-06, copy reviewed for mixed-direction strings | omar + layla |
| R5 | **Shared working tree** — five agents commit from one clone; a commit already landed on the wrong branch once (see §8) | High | High | one `git worktree` per agent, stage only explicit paths (`push_ticket.sh`), re-fetch before every read-back, never `git add -A` | maryam + hakim |
| R6 | **Review bottleneck / capacity** — 8 of 13 tickets sit on one implementer and one reviewer; a single blocked review stalls the whole chain | High | Medium | merge same-day, review in ≤ 2 h, keep PRs small, infra/docs tracks run completely in parallel | maryam |

**The single largest risk is R1 (SQLite write contention)** — it is the one failure that makes the demo look broken in front of an audience, and it is invisible in unit tests that never send two messages at once. It must be load-tested in CHAT-4, before any UI work starts.

---

## 7. Capacity — is this realistic in two days?

Dev-day estimate per ticket (`dev-day` = one focused implementer-day, excluding review):

| Track | Tickets | Estimate |
|---|---|---|
| API | CHAT-1…CHAT-6 | 2h + 3h + 2.5h + 3h + 3.5h + 2h = **16h** |
| Web | CHAT-7, CHAT-8 | 3.5h + 5h = **8.5h** |
| Infra | CHAT-10, CHAT-11 | 1.5h + 2h = **3.5h** |
| Docs / research / copy | CHAT-9, CHAT-12, CHAT-13 | **~4h** |
| **Total** | 13 tickets | **~32h of work** |

Eight of those tickets (1–8, ~24.5 h) are assigned to **one** person, and the API chain is strictly sequential, so they cannot be parallelised without a second implementer. Two days at 8 h/day gives Omar 16 h of the 24.5 h he owns.

**Live progress at 2026-11-19 00:25 UTC** (verified on `origin/dev`): CHAT-1 (PR #1), CHAT-2 (PR #4), CHAT-10 (PR #3) and CHAT-13 (PR #2) are already merged — 9.5 h of the estimate is off the board in the first 25 minutes, so the remaining work is ~22.5 h: CHAT-3/4/5/6/7/8 = 19.5 h on Omar, CHAT-11 = 2 h on yassin, CHAT-12 = 2 h on salim, this plan ~1 h.

**Verdict:** *all 13 tickets merged **and** demoed in two days is not realistic.* After the four early merges, the honest day-2 ceiling is 19.5 h of Omar against 16 h of capacity, before review time — and the web tickets (7, 8 = 8.5 h) are the ones that cannot be parallelised at all.

- **Goal (day 2):** nine tickets on `dev` — CHAT-1, 2, 3, 4, 5, 6, 9, 10, 13 — with CHAT-7 open as a PR. That gives the live API demo: two tokens, a message sent over REST, received on the other socket in under 500 ms.
- **Hedge (day 3):** CHAT-7 and CHAT-8 land, so the §1 demo (two browsers, presence, 360 px RTL) is a **day-3** outcome; CHAT-11 and CHAT-12 also close on day 3. Day 4 is contingency, not plan.

The goal becomes true on day 2 only if **all** of these hold:

1. CHAT-3 lands in the first two hours and its schema is final — no rework in 4 (the `seq` and `client_msg_id` columns are decided once).
2. Reviews happen within 2 hours, not at end of day.
3. CHAT-5 stays in-process, single worker — no queue, no Redis, no multi-process fan-out.
4. The three CHAT-1 gaps (`busy_timeout`, secret guard, 503 health) are closed inside CHAT-3, before the concurrency test.
5. CHAT-7 is built against a stubbed client and only wires the real API on day 2; Layla's 114 keys are already on `dev`, so no string rework.

If any of the five breaks, the honest delivery is the hedge, not the goal.

---

## 8. Notes and open items

- **Drift on the board:** CHAT-9's description says "9 tickets"; the project has 13. Corrected in §2.
- **Branch collision observed 2026-11-19:** commit `0525107` (`docs(web): arabic ui copy for auth chat and states`, Layla's `docs/copy-ar.md`) was committed while the shared clone's HEAD was on `docs/CHAT-9-sprint-plan` and got pushed to that remote branch. It belongs to CHAT-13. This branch was rebuilt from `dev` with only the sprint plan; the file is byte-identical to what merged on `dev` (`blob eb39164` = `dev:docs/copy-ar.md`), and the stray commit is preserved at `refs/heads/rescue/CHAT-13-copy-ar-from-chat9`, so nothing is lost. Root cause is R5.
- **Scope decision — no refresh tokens in Sprint 1:** CHAT-2 shipped a single 60-minute HS256 access token. CHAT-7 therefore keeps the token in memory and sends the user back to `/login` on expiry (AC-03/AC-04). This is a deliberate trade so the web track is not blocked; refresh tokens come with the push-notification ticket.
- **CHAT-1 gaps still open on `dev@08083c6`:** `busy_timeout` pragma missing, `secret_key` has a working default, health has no 503 path. All three are needed by R1's mitigation and are small enough to ride CHAT-3 rather than a new ticket.
- **Open decisions for the owner (Youssef):** (a) accept the 2-day goal + hedge in §7, or re-scope the sprint to the goal only; (b) confirm a second implementer is or is not available — that single answer decides whether all 13 tickets fit.
- **Not in this sprint:** group conversations, attachments/media, message search, push notifications, message editing/deletion, read receipts beyond `last_read_seq`.
