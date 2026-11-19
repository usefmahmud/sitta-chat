# Real-time transport and pagination for sitta-chat

**Ticket:** CHAT-12 · **Author:** Salim (research) · **Date:** 2026-11-19
**Scope:** transport choice for message delivery, history pagination, and ordering/idempotency for `apps/chat-api` (FastAPI + WebSocket + SQLite) and `apps/chat-web` (React + Vite).

**How to read the numbers.** Every figure below is tagged:

- **cited** — taken from the linked source, with the source's own setup described.
- **measured here** — produced by `bench.py` in the research workspace on this machine (Python 3.14.9 stdlib `sqlite3`, local disk, WAL, median of 21 runs). Reproduce with `python3 bench.py`.
- **estimate / reasoning** — derived from the cited facts, not observed.
- `[unverified]` — asserted from general knowledge, no source found in this round.

---

## 1. WebSocket vs SSE vs long-polling in a chat application

### 1.1 What each one actually is

| Transport | Shape | Reconnect built in? | Resume after a gap? |
|---|---|---|---|
| WebSocket (RFC 6455) | HTTP upgrade → full-duplex frame channel | **no** — the protocol has no reconnect semantics; the application reconnects | **no** — no event IDs; the app must track a cursor itself |
| SSE (`text/event-stream`) | one long-lived HTTP response, server→client only | **yes** — `EventSource` reconnects automatically | **yes** — browser resends `Last-Event-ID`, server resumes from it |
| Long-polling | repeated HTTP request/response, each held open until data or timeout | implicit — the client just starts the next request | **yes, if** the request carries a cursor |

WebSocket is an upgrade of an HTTP/1.1 request into a two-way message channel with 2-byte frame headers from server to client.[3] SSE is a single HTTP response of `data:`/`id:`/`event:` lines, always UTF-8, event streams cannot be re-encoded.[1] Long-polling is a plain HTTP request the server holds open ("not immediately reply") and answers only when an event occurs; the client then immediately re-requests.[4]

### 1.2 Latency: the protocol is not the bottleneck

A third-party benchmark (Go server, one core, TLS 1.3, `tc netem` links, 61 million events delivered, median of 5 process runs) reports **identical** one-way delivery latency once the connection is up:[17]

| Link | WebSocket | SSE | Long-poll |
|---|---|---|---|
| LAN | 82 µs | 60 µs | 70 µs |
| 50 ms RTT | 25.2 ms | 25.2 ms | 25.1 ms |
| 200 ms RTT + 1 % loss | 100 ms | 100 ms | 100 ms (p99 100 ms) |

That is ~0.5 RTT for every option: the median is the network, not the framing.[17] The same benchmark measured 99th-percentile on the lossy link at 100 ms for all three; a lost segment costs up to 598 ms of TCP retransmit for every protocol equally.[17]

Where the transports *do* differ is per-message overhead and connection setup:

- **Bytes per 32-byte event:** WebSocket 160 B, SSE 179 B, long-poll 418 B.[17]
- **Bytes per 1 KiB event:** WebSocket 1,154 B, SSE 1,172 B, long-poll 1,412 B.[17]
- **Delivering 1,000 events of ~117 bytes** (a second, independent harness with a byte-counting TCP proxy): WebSocket 119,692 B, SSE 131,596 B, long-poll 884,698 B — 7.4× the payload, of which 569,890 B was HTTP request headers re-sent 1,000 times.[18]
- SSE's per-event price is the `data:` line plus blank-line terminator plus chunked-encoding framing, ~14 bytes.[18]

So: for a chat that sends a few thousand small events per session, **none of the three wins on latency**; the decision is about reconnect behaviour, operational surface, and header overhead.[17][18]

### 1.3 Resource consumption

- **Long-polling** needs, per client, both a TCP connection *and* an outstanding HTTP request held open; sizing must account for both.[4] Every event additionally costs a full request/response with headers.[4][18]
- **SSE** uses one HTTP response per client. Over HTTP/1.1 the browser caps connections per origin at a very low number (**6**), the limit is per browser *and* domain (so all tabs share it), and Chrome/Firefox marked the issue "Won't fix" — the workaround is HTTP/2, where the limit does not apply.[2] The spec authors note the same per-server connection-limit hazard.[1]
- **WebSocket** is one connection, no per-event headers, but keeps a socket and a server task alive for the lifetime of the session.[3][18]
- **Idle cost:** an idle hour costs WebSocket 25.2 KB, SSE 32.2 KB, long-poll 41.6 KB of traffic in the benchmark above.[17] Long-poll's idle cost is the recurring request that must be re-established; SSE's and WebSocket's is keepalive.
- **Keepalive mechanics differ:** WebSocket has first-class Ping/Pong frames — "A Ping frame MAY serve either as a keepalive or as a means to verify that the remote endpoint is still responsive", and a Pong MUST be sent back.[3] SSE has no control frames; the spec recommends a **comment line every ~15 seconds** to survive proxies that drop idle HTTP connections.[1]
- **Proxy idle timeouts will cut an SSE stream:** nginx closes the upstream connection when nothing is read for `proxy_read_timeout`, whose default is **60s**.[5] The 15-second comment heartbeat exists precisely because idle HTTP connections get silently dropped.[1]

### 1.4 Reconnect and gap recovery

- **SSE is the only one that resumes by itself.** The browser reconnects, and if it holds a last event ID it sends it in the `Last-Event-ID` request header; the stream can set a `retry:` field to control the reconnection delay, and a `204 No Content` response tells the client to stop reconnecting entirely.[1] User agents may additionally apply exponential backoff and wait for the network to come back.[1]
- **WebSocket gives you nothing here.** The protocol defines ping/pong and close handshakes but no resume; the benchmark's WebSocket client had to reconnect with `?after=<last id>` and have the server replay from a log — that logic is all application code.[17]
- **Long-polling resumes for free** because the cursor rides in every request, at the cost of a request per event.[4][17]
- **Library-level recovery is best-effort, not a guarantee.** Socket.IO's connection state recovery restores rooms and replays missed packets within `maxDisconnectionDuration`, and its own docs warn: "the recovery **will not always be successful**. That's why you will still need to handle the case where the states of the client and the server must be synchronized".[11]
- Measured catch-up after a forced drop on a 200 ms link: SSE and long-poll recovered 1.3× more events per second than the hand-rolled WebSocket resume path in that harness.[17]

### 1.5 Proxies, CDNs and mobile clients

- **Intermediaries may buffer an entire response**, and "HTTP streaming will not work with such intermediaries" — this is a property of HTTP, not a bug in SSE.[4]
- nginx buffers proxied responses **by default** (`proxy_buffering on`), which would hold an SSE stream; buffering must be disabled for the streaming location, or the upstream must send `X-Accel-Buffering: no`.[5]
- **WebSocket proxying needs explicit configuration** ("requires special configuration and is supported since version 1.3.13" in nginx).[5] Any corporate proxy or load balancer that does not forward the `Upgrade` handshake kills the connection at connect time — the failure is loud, at least.
- **SSE auth has no header escape hatch on the browser side:** the spec builds the `EventSource` request itself, with no author-supplied header list; credentials ride on cookies (`withCredentials: true`) and on the URL.[1] A JWT-in-`Authorization`-header design therefore cannot be reused as-is for SSE.
- **Mobile background delivery is not a socket problem, it is an OS problem.** Apple treats background notifications as low priority, does not guarantee delivery, and throttles them — "don't try to send more than two or three per hour".[19] A suspended app's socket will not carry your messages; you need OS push. `[unverified]` for Android equivalents in this round.

### 1.6 When SSE is enough

SSE is sufficient, and the simpler choice, when **all** of these hold:[1][2]

1. traffic is server→client only (notifications, presence, read receipts, live feed);[2]
2. resume-after-reconnect matters more than sub-millisecond framing cost — SSE gets it from the browser for free;[1][17]
3. you can authenticate with a cookie or a short-lived URL token;[1]
4. you are on HTTP/2, or you accept ≤6 streams per origin across all tabs;[2]
5. you can control the proxy to stop buffering.[5]

For a chat where the user also *types, acks, and marks-read* in real time, that is three of five conditions broken — WebSocket is the right default (see §4).[2][1]

---

## 2. Pagination strategy: offset vs cursor (keyset)

### 2.1 Semantics

`LIMIT n OFFSET m` means "skip the first m rows of the result set, return the next n", where the rows are those produced by the `ORDER BY`.[7] The database must therefore *produce and order* the rows it is about to throw away — `offset` is defined that way by the SQL standard: "the rows in the derived table are first sorted according to the order by clause and then limited by dropping the number of rows specified in the result offset clause".[6] Keyset pagination instead asks for rows strictly after a known position — `WHERE (created_at, id) < (?, ?) ORDER BY created_at DESC, id DESC LIMIT n` — so the index seeks straight to the cursor and reads only `n` rows.[6]

### 2.2 Measured here on SQLite

Setup: 500,000 rows in one `messages` table (450,000 in the test chat), page size 50, index `(chat_id, created_at, id)`, WAL, median of 21 runs, `SELECT id, sender_id, body, created_at` (row values, so the index is not covering). Query plans confirmed by `EXPLAIN QUERY PLAN`: offset → `SEARCH messages USING INDEX idx_msg_chat_created (chat_id=?)`, keyset → `SEARCH ... (chat_id=? AND created_at<?)`.

| Rows skipped | OFFSET (ms) | Keyset (ms) |
|---|---|---|
| 0–49 | 0.050 | 0.049 |
| 1,000–1,049 | 0.090 | 0.054 |
| 10,000–10,049 | 0.496 | 0.053 |
| 50,000–50,049 | **2.225** | **0.054** |

Offset grows linearly with depth and is ~41× slower than keyset at offset 50,000; keyset is flat (~0.05 ms) because it touches only the 50 rows it returns — the shape the SQL standard's definition of `OFFSET` predicts.[6][7] Absolute numbers are this machine's; the shape is the point.

### 2.3 Ordering stability when new messages arrive

The same script demonstrates the failure mode: with rows ordered newest-first, fetch page 1 (ids `[10, 9, 8]`), insert one new row at the head, then fetch page 2 with `OFFSET 3` → `[8, 7, 6]` — **row 8 is delivered twice** and the user scrolls into a duplicate. With keyset (`WHERE id < 8`) page 2 is `[7, 6, 5]` — **no overlap**. Deleting a row between fetches has the mirror-image bug: offset skips a row that the user never sees. This is a direct consequence of `OFFSET` being defined relative to a result set that has since changed.[6][7]

Practical consequences:

- **Infinite scroll / "load older messages" — keyset only.** The timeline grows at the head, which is exactly the case where `OFFSET` is unstable.
- **Random page jumps** ("go to page 37") are what offset is good at; keyset cannot do it without a lookup table, and chat UIs do not need it.[6][15]
- **Stable ties need a unique tiebreaker.** Order by `(created_at, id)`, never `created_at` alone, otherwise rows sharing a timestamp can be duplicated or skipped across pages. Index it in that exact order — SQLite's planner will only use the index for both search and sort when the index order matches the `ORDER BY`.[10]
- **`id` must be monotonic for the tiebreaker to be meaningful.** In SQLite a plain `INTEGER PRIMARY KEY` is the rowid and gets "an unused integer, usually one more than the largest ROWID currently in use"; only `AUTOINCREMENT` guarantees no reuse of ROWIDs after deletes.[8]

### 2.4 Cost summary

| | OFFSET | Keyset/cursor |
|---|---|---|
| Rows touched per request | offset + limit[6] | limit (index seek)[6] |
| Deep history | degrades linearly (measured: 2.2 ms @ 50k here) | flat (0.054 ms) |
| New rows arriving | duplicates / skips (measured) | stable |
| Random access to page N | yes | no |
| Client contract | page number | opaque cursor (e.g. `before_id`) |
| Real-world precedent | — | Stripe list endpoints: `starting_after` / `ending_before` object IDs, reverse-chronological, `limit` 1–100[15] |

---

## 3. Ordering and delivery guarantees

### 3.1 Server-assigned sequence numbers

Total order must be decided by one authority, not by client clocks. Telegram's secret chats make this explicit: every message carries a `seq_no`, initialised at `(0,0)` and "incremented strictly by 1 after any message (service or not) is sent/received and processed", and clients use the counter (plus a dedicated resend action) to detect reordering, replay, omission and gaps.[12]

For a single-process FastAPI + SQLite service the equivalent is a per-chat counter:

```sql
-- one transaction, one writer
INSERT INTO messages (chat_id, sender_id, body, created_at, client_msg_id)
VALUES (:chat, :sender, :body, :now, :client_msg_id)
RETURNING id, seq;
```

- SQLite WAL allows many readers but **"one writer at a time"**, and checkpoints cannot pass an active reader.[9] Assigning `seq` inside that single write transaction is therefore race-free without extra locking — **reasoning from [9]**, not a measurement.
- `(chat_id, seq)` should be `UNIQUE`; `seq` is what the client stores as `last_seq` and what the reconnect backfill asks for. Sorting by `seq` also makes the pagination cursor of §2 exact.

### 3.2 Idempotency keys for sends

The retry problem is not "did it fail" but "did it succeed before it failed". The standard answer is a client-generated key that the server uses to recognise a retry:[13][14]

- The **client** generates the key — Stripe suggests "V4 UUIDs, or another random string with enough entropy", max 255 chars, and warns against putting personal data in it.[13]
- The **server** stores the outcome of the first request and returns the *saved* response to retries with the same key; Stripe keeps v1 results for at least 24 hours and errors if the same key arrives with different parameters.[13]
- The IETF `Idempotency-Key` header draft exists to make this a standard HTTP contract for non-idempotent methods such as POST/PATCH.[14]

In a chat API the natural key is a **`client_msg_id` (UUIDv4) generated once per composed message**, reused verbatim on every retry, with `UNIQUE(sender_id, client_msg_id)`. On conflict the server returns the existing `(id, seq)` instead of inserting a second row — **design inference** from [13], not observed in this repo yet.

### 3.3 End-to-end exactly-once does not exist

Every transport here is at-least-once in practice: TCP retransmits, and both SSE and WebSocket can drop a segment across a disconnect.[17] Idempotency (server side) + dedupe (client side, by `client_msg_id` / `seq`) is what makes retries safe; it is not a delivery guarantee.[13] Delivery states a chat UI actually shows — sent (server ack) → delivered (peer ack) → read — each need their own event, and each inherits the same duplicate risk and the same sequence/dedupe discipline.[12] The exact receipt-state ladder for our UI is `[unverified]` in this round.

### 3.4 What "resume" means concretely

1. client keeps `last_seq` per chat, persisted locally;
2. on (re)connect it calls `GET /chats/{id}/messages?after_seq=last_seq` — plain HTTP, no socket tricks — and merges by `seq`, deduping by `client_msg_id`;[7][15]
3. only then does the socket subscribe for live events and drop any live event whose `seq` is ≤ what the backfill already delivered;[11][17]
4. sends wait in a client outbox with their `client_msg_id` until an ack returns `(id, seq)`.[13][14]

FastAPI already gives the primitives for this: a `WebSocket` endpoint per chat, `websockets` as the server dependency, and `WebSocketDisconnect` raised when a client drops.[16] This is the same shape as Socket.IO's recovery (replay missed packets, but keep a resync path because recovery can fail)[11] and the same shape as the benchmark's WebSocket resume, which had to be written by hand.[17]

---

## 4. Recommendation for sitta-chat

**Five decisions:**

1. **WebSocket is the primary real-time transport** for messages, typing and presence — one `/ws` endpoint, token checked at handshake, one socket per tab. The user sends as well as receives, so SSE's one-way limitation and its per-origin 6-stream cap both bite, and WebSocket removes the per-event headers where long-polling loses 7.4× the bytes.[2][18]
2. **Every message gets a server sequence number per chat, assigned in the same SQLite write transaction as the insert**, with `UNIQUE(chat_id, seq)`.[9][12] WAL's single-writer rule[9] makes that safe; the client's single source of truth becomes `seq`, not `created_at`.
3. **All history reads are cursor-based:** `GET /chats/{id}/messages?before_seq=<n>&limit=50` for "load older", `after_seq=<n>` for reconnect backfill. No `OFFSET` on the message timeline: measured 41× slower at depth and it duplicates rows when messages arrive.[6][7][15]
4. **Sends are idempotent by `client_msg_id` (UUIDv4)** generated on the client once per message,[13] `UNIQUE(sender_id, client_msg_id)`, returning the original `(id, seq)` on retry.[13][14]
5. **Keep a plain-HTTP fallback that shares the same contract.** Because WebSocket can be blocked by proxies that need special configuration[5], and because library-level recovery is explicitly best-effort[11], the API should expose the same `after_seq` backfill over HTTP so a degraded client can poll or stream SSE when the socket will not connect.

**What to avoid:**

- ❌ **`OFFSET` pagination on the message list** — the measured duplicate-row bug is visible to users as a repeated bubble every time a new message lands mid-scroll.
- ❌ **Ordering by client timestamps or `created_at` alone** — phones' clocks drift and equal timestamps tie; use `(seq)` for order and `(created_at, id)` only if a human-readable sort key is genuinely needed.[8][12]
- ❌ **Fire-and-forget sends without an idempotency key** — a retried POST after a timeout is the single most common way a chat shows duplicate messages.[13]
- ❌ **A hand-rolled reconnect that only pings** — WebSocket gives no resume semantics[3]; ping keeps the socket alive, it does not recover the messages sent while it was dead.
- ❌ **Relying on in-memory connection state across multiple uvicorn workers** — the socket registry and per-chat broadcast would live in one process while SQLite is shared; run one worker for now, or add a shared bus before scaling out — **reasoning from [9]**, untested here.
- ❌ **SSE through a default-configured reverse proxy** — `proxy_buffering on` plus a 60s `proxy_read_timeout` will hold or kill the stream; you need `X-Accel-Buffering: no` and a heartbeat comment every ~15s.[1][5]
- ❌ **Assuming the socket survives the app going to the background** — background delivery needs OS push; Apple throttles background notifications to "two or three per hour" and does not guarantee them.[19]

---

## Limits of this research

- All performance numbers are either **third-party benchmarks**[17][18] or **measured on this machine's local SQLite file**; nothing was measured under production load, over a real mobile network, or through our own reverse proxy.
- SSE-over-HTTP/2, WebSocket compression (`permessage-deflate` cut bytes to 0.26× payload in one harness[18]), and FastAPI/uvicorn's WebSocket throughput were **not** benchmarked here.
- Android background-delivery behaviour was not sourced in this round — marked `[unverified]`.
- The `seq` design assumes a single-process writer; the multi-worker/multi-node variant (shared sequence allocator, Redis/NATS fan-out) is out of scope for CHAT-12.

## Sources

[1] https://html.spec.whatwg.org/multipage/server-sent-events.html
[2] https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events
[3] https://datatracker.ietf.org/doc/html/rfc6455
[4] https://datatracker.ietf.org/doc/html/rfc6202
[5] https://nginx.org/en/docs/http/ngx_http_proxy_module.html
[6] https://use-the-index-luke.com/no-offset
[7] https://www.sqlite.org/lang_select.html
[8] https://www.sqlite.org/autoinc.html
[9] https://www.sqlite.org/wal.html
[10] https://www.sqlite.org/queryplanner.html
[11] https://socket.io/docs/v4/connection-state-recovery
[12] https://core.telegram.org/api/end-to-end/seq_no
[13] https://docs.stripe.com/api/idempotent_requests
[14] https://datatracker.ietf.org/doc/html/draft-ietf-httpapi-idempotency-key-header
[15] https://docs.stripe.com/api/pagination
[16] https://fastapi.tiangolo.com/advanced/websockets
[17] https://robertz.co/benchmarks/protocols/websocket-vs-sse-vs-long-polling-vs-mqtt
[18] https://theinfinity.dev/articles/websocket-vs-sse-vs-polling
[19] https://developer.apple.com/documentation/usernotifications/pushing-background-updates-to-your-app
