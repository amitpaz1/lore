# Story 11: Docker Image + Deployment + Docs

**Batch:** 10 | **Est:** 3-4h | **Dependencies:** Story 10

## Description

Create a production-ready Docker image, deploy the managed instance to fly.io, and write documentation for self-hosted setup, API reference, and MCP configuration.

## Acceptance Criteria

1. `Dockerfile.server` produces a slim production image (< 200MB)
2. Docker image runs migrations on startup automatically
3. `docker compose -f docker-compose.yml up` works for self-hosted deployment (production config, no hot-reload)
4. fly.io deployment: `fly deploy` succeeds and server is reachable at public URL
5. Health check passes on deployed instance
6. README.md updated with Phase 2 sections: server setup, remote SDK usage, MCP setup
7. `docs/self-hosted.md` — step-by-step self-hosted guide (Docker Compose)
8. `docs/api-reference.md` — all endpoints with request/response examples
9. `docs/mcp-setup.md` — Claude Desktop and OpenClaw MCP configuration guide
10. `pyproject.toml` updated with `[remote]` and `[mcp]` optional dependency groups
11. Server image tagged and pushed to Docker Hub or GitHub Container Registry

## Technical Notes

- Production Dockerfile: multi-stage build, no dev dependencies
- fly.toml for fly.io configuration
- Fly Postgres for managed DB (pgvector supported)
- Docs should include copy-pasteable config snippets
- API reference can be auto-generated from FastAPI's OpenAPI spec + manual examples
- Update `pyproject.toml` version to 0.2.0
