# Deploying sitta-chat

Two containers, built from this repo, talking over a private compose network:

```
                host:${WEB_PORT:-8080}
                        │
                 ┌──────▼──────┐        /api/, /ws/        ┌──────────────┐
                 │     web     │ ─────────────────────────▶ │     api      │
                 │ nginx :80   │   (upstream `api:8000`)    │ uvicorn :8000│
                 └─────────────┘                            └──────┬───────┘
                                                                   │ sqlite
                                                            ┌──────▼───────┐
                                                            │  chat_data   │
                                                            │ named volume │
                                                            └──────────────┘
```

- `web` is the only container with a published port. `api` uses `expose`, so it is reachable
  from the web container and **not** from the host or the internet.
- `web` proxies `/api/` (HTTP) and `/ws/` (websocket upgrade) to `api:8000`, which means the
  browser talks to one origin and no CORS dance is needed in production.
- `api` runs as an unprivileged user (`uid 10001`) and keeps its database at
  `/app/data/chat.db`, backed by the named volume `sitta-chat-data`.

Nothing in this repository starts a container on its own. Running it — and especially
publishing it — is the owner's call; this file is the plan, not an automatic deployment.

## Prerequisites

- Docker Engine 24+ with the compose plugin (`docker compose version`).
- A host directory with the repo cloned.
- A `.env` next to `docker-compose.yml` (copy `.env.example`, then set a real
  `CHAT_SECRET_KEY`). Compose refuses to render without it — that is deliberate.

## Build and start

```bash
cp .env.example .env          # then edit CHAT_SECRET_KEY and WEB_PORT
docker compose build
docker compose up -d
docker compose ps             # both services must show (healthy)
```

First check after a start:

```bash
curl -fsS http://127.0.0.1:8080/api/health      # api health, through the web container
docker compose logs --tail=50 api web
```

## Configuration

| Variable | Where | Default | Notes |
|---|---|---|---|
| `WEB_PORT` | compose | `8080` | host port for the web container |
| `CHAT_ENVIRONMENT` | api | `production` | free-form label, `development` also accepted |
| `CHAT_SECRET_KEY` | api | — | **required**, JWT signing key; generate with `openssl rand -hex 32` |
| `CHAT_DATABASE_URL` | api | `sqlite:////app/data/chat.db` | pinned in compose so the db stays on the volume |
| `CHAT_ACCESS_TOKEN_TTL_MINUTES` | api | `60` | token lifetime |
| `CHAT_CORS_ORIGINS` | api | `["http://localhost:8080"]` | JSON list; only needed if the UI is served from another origin |
| `VITE_API_BASE_URL` | web (build arg) | `/api` | inlined at build time — change it and rebuild |

Secrets live in `.env` only. They are never baked into an image: `.env*` and `data/` are
excluded by both `.dockerignore`s and by the repo `.gitignore`.

## Healthchecks

Both images declare a `HEALTHCHECK`, and compose repeats them so `docker compose ps` and
`depends_on: condition: service_healthy` work the same everywhere.

| Service | Probe | Interval / timeout / retries |
|---|---|---|
| `api` | `GET http://127.0.0.1:8000/api/health` (also checks the database) | 30s / 5s / 3, 20s start period |
| `web` | `wget --spider http://127.0.0.1/` | 30s / 5s / 3, 10s start period |

A restart policy of `unless-stopped` keeps both up across reboots; an unhealthy container is
reported but *not* restarted automatically — check the logs before restarting anything.

## Data: backup and restore

The database is one sqlite file (WAL mode) inside `sitta-chat-data`. Stop the api for a
consistent copy, or use sqlite's online backup while it runs.

```bash
# consistent backup (api stopped)
docker compose stop api
docker run --rm -v sitta-chat-data:/data -v "$PWD/backups":/backup alpine \
  tar czf /backup/chat-$(date +%Y%m%d-%H%M).tar.gz -C /data .
docker compose start api

# restore (overwrites the current database — ask before doing this)
docker compose stop api
docker run --rm -v sitta-chat-data:/data -v "$PWD/backups":/backup alpine \
  sh -c 'rm -rf /data/* && tar xzf /backup/<file>.tar.gz -C /data'
docker compose start api
```

Keep backups outside the volume, and never delete a volume (`docker compose down -v`) without
the owner's explicit approval — that command destroys the database.

## Upgrades and rollback

```bash
git pull
docker compose build
docker compose up -d          # recreates only the containers whose image changed
docker compose ps
```

Rollback is the same steps on the previous commit; the named volume survives rebuilds. The
sqlite file changes shape only through the api's migrations, so a rollback of the image
implies rolling back the schema too — take a backup first.

## Known limits of this setup

- Single host, single api replica: sqlite and in-process websocket state do not scale
  horizontally. Scaling out means a shared database and a broker — out of scope here.
- TLS termination and the public reverse proxy are **not** part of this compose file. The web
  container speaks plain HTTP on the host port; anything that exposes it to the internet is a
  separate, owner-approved step.
- `web` resolves `api` at start-up; if the api container is recreated with a new address,
  restart `web` as well (compose does this for you on `up -d`).
