# Phase 2 PRD — Lore Cloud & Org-Wide Sharing

**Author:** John (Product Manager) | **Date:** 2026-02-12
**Status:** Draft — reviewed and challenged
**Depends on:** [Phase 2 Brief](./phase2-brief.md), [Phase 1 PRD](./prd.md)

---

## 1. Product Summary

Lore Phase 2 adds a server component and RemoteStore SDK implementation so agents across machines can share lessons through a central API. The local SDK continues to work standalone — cloud is additive.

**MVP definition:** The smallest thing that lets two agents on different machines share lessons through a Lore server, with org-scoped API key auth.

---

## 2. User Stories (MVP)

### Story 1: Set up an org
> As a team lead, I want to create a Lore org and get an API key so my agents can share lessons.

**Acceptance criteria:**
- `lore server init` creates an org and prints a root API key
- Org has a name and unique ID
- Root API key can create sub-keys
- Self-hosted: runs via Docker or direct binary
- Managed: sign up at lore.dev, get key

### Story 2: Publish a lesson remotely
> As an agent developer, I want my agent to publish lessons to the org's server so other agents can access them.

**Acceptance criteria:**
- `Lore(store="remote", api_key="lore_...", url="https://...")` connects to server
- `lore.publish(...)` sends lesson to server via API
- Lesson is redacted client-side BEFORE sending (redaction happens in SDK, not server)
- Server stores lesson scoped to the org
- Publish returns lesson ID
- Latency: < 500ms p95 over network

### Story 3: Query lessons remotely
> As an agent developer, I want my agent to query the org's shared lessons.

**Acceptance criteria:**
- `lore.query("...")` hits server API with embedding computed client-side
- Server performs tag filtering + cosine similarity
- Results include relevance score, same as local
- Query latency: < 300ms p95 for 10K lessons
- Works identically to local query from the developer's perspective

### Story 4: Scope lessons by project/team
> As a team lead, I want to organize lessons by project so agents only see relevant lessons.

**Acceptance criteria:**
- Lessons have `project` field (already in schema)
- API keys can be scoped to a project: key X can only read/write project "backend-agents"
- Unscoped keys access all projects in the org
- Query can filter by project

### Story 5: Manage API keys
> As an admin, I want to create, list, and revoke API keys for my org.

**Acceptance criteria:**
- Root key can: create keys, list keys, revoke keys
- Keys have: name, optional project scope, created_at, last_used_at
- Revoked keys immediately stop working
- Keys are hashed in storage (never stored in plaintext)
- CLI: `lore keys create --name "prod-agent" --project "backend"`
- API: `POST /v1/keys`, `GET /v1/keys`, `DELETE /v1/keys/:id`

### Story 6: All existing SDK features work remotely
> As a developer, I want upvote/downvote, confidence decay, export/import, and prompt helpers to work the same way against the remote store.

**Acceptance criteria:**
- `lore.upvote()`, `lore.downvote()` work via API
- `lore.as_prompt()` works (it already operates on query results, not store)
- Confidence decay computed server-side during query
- Export/import work via bulk API endpoints

### Story 7: MCP server for zero-code agent integration
> As an agent user, I want to add Lore as an MCP tool so my AI agents can save and recall lessons without any code changes.

**Acceptance criteria:**
- `lore mcp` starts an MCP server (stdio transport) exposing Lore operations as tools
- **Tools exposed:**
  - `save_lesson` — maps to `lore.publish()` (params: problem, resolution, context?, tags?, project?)
  - `recall_lessons` — maps to `lore.query()` (params: query, tags?, project?, limit?)
  - `upvote_lesson` — maps to `lore.upvote()` (params: lesson_id)
  - `downvote_lesson` — maps to `lore.downvote()` (params: lesson_id)
- Works with local SqliteStore (default) or RemoteStore (when api_url + api_key configured)
- Configurable via environment variables: `LORE_STORE` (local|remote), `LORE_API_URL`, `LORE_API_KEY`, `LORE_PROJECT`
- Claude Desktop config: add to `mcpServers` in claude_desktop_config.json and it just works
- OpenClaw: installable as a skill — agents get memory tools automatically
- Agent decides when to save/recall — no developer instrumentation needed
- Tool descriptions include clear guidance so LLMs know when to use each tool

---

## 3. What's the MVP? (Ruthlessly scoped)

**IN scope:**
- [ ] FastAPI server with Postgres backend
- [ ] Org + API key creation and management
- [ ] Publish endpoint (with project scoping)
- [ ] Query endpoint (embedding similarity + tag filtering)
- [ ] Upvote/downvote endpoints
- [ ] RemoteStore implementation in Python SDK
- [ ] RemoteStore implementation in TypeScript SDK
- [ ] Docker image for self-hosted
- [ ] Basic rate limiting (100 req/min per key)
- [ ] MCP server exposing Lore tools (save_lesson, recall_lessons, upvote, downvote)
- [ ] MCP server works with both SqliteStore and RemoteStore

**OUT of scope for Phase 2:**
| Feature | Why it's out |
|---|---|
| Hybrid local+remote sync | Distributed systems problem. Too complex. Pure remote is fine for MVP. |
| Community/public sharing | No users yet. Premature. |
| LLM-powered redaction | Cloud premium feature, not MVP. Regex redaction still runs client-side. |
| Analytics dashboard | Nice but not needed. Ship logs, add dashboard later. |
| Web UI for org management | CLI + API is enough. No frontend. |
| SSO / OAuth | API keys only. Simple auth. |
| Multi-org per user | One org per deployment for now. |
| Webhooks / event streaming | Polling is fine for MVP. |
| TypeScript server | One server (Python/FastAPI). Both SDKs connect to it. |
| Billing / payment integration | Free tier only at launch. Add Stripe later. |

---

## 4. Hybrid Mode: Deferred

Original plan included local cache + remote sync. **Deferred to Phase 3.**

Why:
- Conflict resolution (two agents update same lesson offline) is hard
- Sync ordering, retry queues, eventual consistency — each is a week of work
- MVP can validate remote sharing without hybrid
- If users strongly request offline-first with sync, build it then

**Phase 2 stance:** RemoteStore is online-only. If server is unreachable, operations fail with clear error. SDK user can wrap in try/catch and fall back to local store themselves.

---

## 5. Success Metrics

| Metric | Target (3 months post-Phase 2 launch) | Why |
|---|---|---|
| Self-hosted deployments | 30+ | Proves the server is useful |
| Managed cloud orgs | 20+ | Proves managed has demand |
| Lessons published via remote | 50K+ | Shows agents are actually sharing |
| Agents per org (median) | 3+ | Multi-agent sharing is happening |
| API key creation per org | 2+ | Teams are onboarding multiple agents |
| Time from signup to first remote publish | < 15 min | DX quality signal |
| Paying customers (Team+) | 10+ | Revenue validation |

---

## 6. SDK Interface Changes

**Zero breaking changes.** Cloud is a new store backend, not a new API.

```python
# Phase 1 (still works, always will)
lore = Lore()  # local SQLite

# Phase 2 addition
lore = Lore(
    store="remote",
    api_url="https://api.lore.dev",  # or self-hosted URL
    api_key="lore_sk_...",
)

# Everything else is identical
lore.publish(problem="...", resolution="...", tags=["..."])
lessons = lore.query("...", tags=["..."], limit=5)
```

```typescript
// Phase 2 TypeScript
const lore = new Lore({
  store: "remote",
  apiUrl: "https://api.lore.dev",
  apiKey: "lore_sk_...",
});
```

---

## Review Notes — Challenges to John's Phase 2 Output

### What I pushed back on:

1. **Original MVP included hybrid sync.** Killed it. This alone could take 3 weeks. Remote-only is the MVP. If the server is down, operations fail. Simple, honest, shippable.

2. **Original had 12 user stories.** Cut to 6. Stories for "analytics," "team management UI," "webhook notifications" are all nice-to-haves that bloat scope. An admin CLI for key management is enough.

3. **"Can a solo dev ship this in 2-3 weeks?"** With this scope: yes.
   - Week 1: Server (FastAPI + Postgres + auth + CRUD endpoints)
   - Week 2: RemoteStore SDK (Python + TypeScript) + Docker image
   - Week 3: Testing, docs, deploy managed instance
   - It's tight but the existing Store interface means RemoteStore is mostly HTTP calls mapping to the same methods.

4. **Embedding computation: client vs server?** Decision: **client-side**. The SDK already has the embedding model. Sending raw text to the server means the server needs the model too (cost, complexity). Client computes embedding, sends vector + text to server. Server just stores and does cosine similarity on stored vectors. This keeps the server dead simple.

5. **Redaction: client vs server?** Decision: **client-side**. Redaction must happen BEFORE data leaves the machine. This is a security invariant. The server never sees unredacted data. This is a feature, not a limitation.
