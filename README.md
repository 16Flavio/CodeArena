# CodeArena

A self-hostable programming-contest platform with a bilingual (FR/EN) learning section.

CodeArena runs two kinds of contests:

- **Output-only contests** (Hashcode-style): teams download an instance, compute a result offline, and upload the output file. Scoring is done by a contest-specific Python validator, sandboxed in a throwaway Docker container.
- **ICPC-style contests**: contestants submit source code (C, C++, Python, …) which is compiled and run against hidden testcases — with verdicts (AC/WA/TLE/RTE/CE), penalty time, scoreboard freeze, subtask partial credit, interactive problems, and DOMjudge package import.

The **Learn** section serves seeded lessons (French + English) with KaTeX math, interactive visualization widgets, and inline graded coding exercises.

## Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI + SQLAlchemy + Alembic, JWT auth with optional TOTP 2FA |
| Frontend | React 19 + Vite + Tailwind, i18next (full FR/EN parity) |
| Database | PostgreSQL 16 in production, SQLite for local dev |
| Queue | Redis + RQ (horizontally scalable workers), in-process fallback for dev |
| Sandboxing | Sibling Docker containers: no network, read-only rootfs, cap-drop=ALL, non-root, memory/CPU/pids limits |

## Quick start (local dev)

```bash
bash start.sh    # backend on :8000, frontend on :5173, SQLite at ./contest.db
bash stop.sh
```

The first registered user automatically becomes admin.

## Tests

```bash
python -m pytest backend/tests -q        # backend (in-memory SQLite, no setup needed)
cd frontend && npm run test:e2e          # Playwright smoke suite (throwaway backend + DB)
cd frontend && npx eslint src --max-warnings=50
```

CI runs the backend suite, the full Alembic chain from zero against Postgres 16 (catches SQLite-only migrations), ESLint + the Vite build, and the Playwright smoke suite.

## Production deployment

```bash
cp .env.example .env    # set SECRET_KEY, POSTGRES_PASSWORD, SCORING_MODE=docker, ...
docker compose --profile build-only build scoring-image icpc-sandbox-image
docker compose up -d --build
docker compose run --rm backup          # timestamped pg_dump + uploads tarball
```

See **[docs/DEPLOY.md](docs/DEPLOY.md)** for the full runbook: Postgres sizing, worker scaling, TLS/Caddy edge, backup/restore, migration discipline, and the security model (what runs sandboxed, what the Docker socket mount implies, 2FA recovery).

> **Security note:** `SCORING_MODE=docker` is required for anything public — it isolates both organizer-authored validators and contestant-submitted code in locked-down containers. `subprocess` mode is for trusted classroom use only, and ICPC judging refuses to run (fails closed) if docker mode is configured but the daemon is unreachable.

## Repository layout

```
backend/            FastAPI app — routers/, models.py, scoring pipeline, ICPC judge
backend/alembic/    migrations (must work on both SQLite and Postgres)
backend/tests/      pytest suite
frontend/           React app — src/pages, src/components, src/i18n/{fr,en}.json
scripts/seed_chapterN/  Learn-section lesson seeds (FR/EN markdown pairs)
scripts/seed_widgets/   interactive widget catalog for lessons
docs/DEPLOY.md      production runbook
```

## Adding Learn content

Each chapter is an idempotent seed script with paired `*.fr.md` / `*.en.md` lesson files:

```bash
python scripts/seed_chapter1/seed_chapter1.py            # validates then seeds
python scripts/seed_chapter1/seed_chapter1.py --validate-only
```

Lessons follow a fixed 3-part format — intuition, algorithm + proof + complexity, then three graded inline exercises — and seeding preserves student progress.
