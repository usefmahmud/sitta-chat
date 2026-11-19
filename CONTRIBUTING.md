# Contributing

## Branching model

```
main        production — only receives merges from staging
 └ staging  release candidate — only receives merges from dev
    └ dev   integration — the working branch, PRs land here
       └ feat/CHAT-12-send-message   one branch per ticket
```

**Every ticket gets its own branch**, cut from an up-to-date `dev`:

```bash
git checkout dev && git pull
git checkout -b feat/CHAT-12-send-message
```

Branch name pattern (enforced in CI):

```
<type>/CHAT-<number>-<kebab-slug>
type = feat | fix | chore | docs | refactor | test | ci
```

## Commit messages — commitlint, non-negotiable

Format: `type(scope): subject`

```bash
git commit -m "feat(messages): send a message over websocket"
git commit -m "fix(auth): reject expired refresh tokens"
git commit -m "docs(api): document the message envelope"
```

Rules (see `commitlint.config.js`):

- `type` ∈ `feat fix docs style refactor perf test build ci chore revert`
- `scope` ∈ `api web auth chat messages realtime presence notifications search infra ci deps docs release`
- subject **lower-case**, no trailing period, header ≤ **72 chars**

The commit is rejected locally (husky hook) **and** in CI. A red CI cannot be merged.

## Pull requests

- Target `dev`, never `main` directly.
- Fill the PR template: ticket, what changed, **the command you ran and its real output**.
- One ticket per PR; keep it small enough to review in one sitting.

## Definition of done

- [ ] Tests pass locally and in CI
- [ ] `commitlint` is green
- [ ] The ticket is moved to `review` on the board
- [ ] No secrets, no `.env`, no database files in the diff
