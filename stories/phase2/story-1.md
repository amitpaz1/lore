# Story 1: Docker Compose with FastAPI + pgvector Postgres

**Batch:** 1 | **Est:** 1.5-2h | **Dependencies:** None

## Description

Set up the development environment: a Docker Compose file that runs a FastAPI server and a PostgreSQL database with pgvector. The FastAPI app should have a health endpoint and connect to the database on startup.

## Acceptance Criteria

1. `docker compose up` starts both services without errors
2. `GET /health` returns `{"status": "ok"}` with HTTP 200
3. PostgreSQL is accessible on port 5432 (from within Docker network)
4. pgvector extension is available (`SELECT * FROM pg_extension WHERE extname = 'vector'` succeeds after init)
5. FastAPI auto-reload works in dev mode (code changes reflect without restart)
6. `docker compose down -v` cleanly removes containers and volumes
7. Environment variables for DATABASE_URL are configurable via `.env` or compose file

## Technical Notes

- Use `pgvector/pgvector:pg16` as the Postgres image
- FastAPI app at `src/lore/server/app.py`
- Dockerfile.server for the API service (Python 3.11-slim base)
- Expose API on port 8765
- Use lifespan context manager for DB connection pool setup/teardown
- Dev compose should mount source code as volume for hot reload
