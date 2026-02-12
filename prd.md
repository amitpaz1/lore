# Product Requirements Document — Lore SDK

**Author:** John (Product Manager) | **Date:** 2026-02-12
**Status:** Draft — reviewed and challenged (see Review Notes at bottom)
**Depends on:** [Product Brief](./product-brief.md)

---

## 1. Product Summary

Lore is an open-source SDK (Python + TypeScript) that lets AI agents publish operational lessons and query lessons from other agents, with built-in redaction. The MVP is a **local-first library** — no server required.

---

## 2. Core User Stories (MVP)

### Story 1: Publish a lesson
> As an agent developer, I want my agent to save a lesson it learned during execution so that other agents (or future runs) can benefit from it.

**Acceptance criteria:**
- `lore.publish(lesson)` takes < 5 lines of code to integrate
- Lesson includes: context/tags, problem, resolution, confidence (0-1)
- Lesson is redacted before storage (PII/secrets stripped)
- Lesson is persisted to local store (SQLite default)

### Story 2: Query for relevant lessons
> As an agent developer, I want my agent to query for lessons relevant to its current task before attempting it.

**Acceptance criteria:**
- `lore.query("how to handle rate limits on Stripe API")` returns ranked results
- Supports semantic search (embedding-based) and tag filtering
- Results include relevance score
- Query returns in < 200ms for local store with 10K lessons
- Zero-result case is handled gracefully (empty list, not error)

### Story 3: Redact sensitive data
> As an agent developer, I want lessons to be automatically scrubbed of API keys, PII, and secrets before storage.

**Acceptance criteria:**
- Default redaction catches: API keys, emails, phone numbers, IP addresses, credit card numbers
- Redaction runs automatically on publish (opt-out, not opt-in)
- Redacted content replaced with `[REDACTED:type]` tokens
- Developer can add custom redaction patterns

### Story 4: Use lessons in agent prompt
> As an agent developer, I want a helper that formats retrieved lessons into a system prompt section.

**Acceptance criteria:**
- `lore.as_prompt(lessons)` returns a formatted string ready for system prompt injection
- Includes lesson context, resolution, and confidence
- Truncates to fit token budget (configurable, default 1000 tokens)

### Story 5: Lesson lifecycle
> As an agent developer, I want lessons to have confidence decay so stale lessons don't mislead my agent.

**Acceptance criteria:**
- Lessons have `created_at` and optional `expires_at`
- Query results deprioritize old lessons (configurable decay)
- Developer can upvote/downvote lessons programmatically (`lore.upvote(id)`, `lore.downvote(id)`)
- Lessons can be deleted

---

## 3. Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| F1 | Publish lessons with structured schema | Must |
| F2 | Query lessons via semantic search | Must |
| F3 | Tag-based filtering on queries | Must |
| F4 | Automatic PII/secret redaction on publish | Must |
| F5 | Custom redaction patterns | Should |
| F6 | Prompt formatting helper | Must |
| F7 | Confidence decay over time | Should |
| F8 | Upvote/downvote lessons | Should |
| F9 | Export/import lessons (JSON) | Should |
| F10 | Multiple storage backends (SQLite default, Postgres optional) | Could |

---

## 4. Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NF1 | Query latency (local, 10K lessons) | < 200ms p95 |
| NF2 | Publish latency (local) | < 100ms p95 |
| NF3 | SDK install size | < 50MB (including embedding model) |
| NF4 | Zero external service dependencies for local mode | Hard requirement |
| NF5 | Python 3.9+ and Node 18+ support | Hard requirement |
| NF6 | Redaction must never leak raw secrets in stored data | Hard requirement |
| NF7 | Works offline (no internet required for local mode) | Hard requirement |

---

## 5. The "Aha Moment"

**First-run experience (must take < 5 minutes):**

```python
pip install lore-sdk

# In your agent code:
from lore import Lore

lore = Lore()  # local SQLite, zero config

# After your agent learns something:
lore.publish(
    problem="Stripe API returns 429 after 100 requests/min",
    resolution="Add exponential backoff starting at 1s, cap at 32s",
    tags=["stripe", "rate-limit", "api"],
    confidence=0.9
)

# Before your next agent run:
lessons = lore.query("stripe rate limiting", limit=3)
prompt_section = lore.as_prompt(lessons)
# Inject into your agent's system prompt
```

**If this doesn't feel magical in 5 minutes, we've failed.**

---

## 6. Success Metrics

| Metric | Target (3 months post-launch) | Why it matters |
|--------|-------------------------------|----------------|
| PyPI + npm weekly downloads | 500+ | Adoption signal |
| GitHub stars | 1,000+ | Visibility / credibility |
| Repeat usage (>1 publish per week per user) | 30%+ of active users | Proves it's actually useful, not just tried once |
| Lessons published | 10,000+ total | Network effects start here |
| Time to first lesson published | < 5 min | DX quality signal |
| "Would you be upset if you could no longer use Lore?" | 40%+ "very upset" | PMF signal (Sean Ellis test) |

---

## 7. Explicitly OUT of Scope for v1

| Feature | Why it's out |
|---------|-------------|
| Hosted cloud service | Solo dev. Prove local value first. Add cloud later. |
| Cross-team sharing over network | Requires auth, networking, trust model. Too complex for MVP. |
| Community/public lesson marketplace | Quality curation unsolved. Way too early. |
| Web UI / dashboard | CLI and SDK only. Don't build UI until you need it. |
| LLM-powered redaction | Expensive, slow, needs API keys. Regex-based is good enough for v1. |
| Agent framework plugins (LangChain, CrewAI) | Nice to have but the raw SDK must work first. Add thin wrappers in v1.1. |
| Multi-modal lessons (images, files) | Text only. Keep it simple. |
| Real-time sync between agents | Polling or manual refresh is fine for MVP. |

---

## 8. Open Questions

1. **Embedding model:** Ship a small local model (e.g., all-MiniLM-L6-v2 at ~80MB) or require users to provide their own? Recommendation: ship one, allow override.
2. **Lesson schema strictness:** Enforce `problem` + `resolution` fields, or allow freeform? Recommendation: enforce minimal structure but allow extra fields.
3. **Namespace/scoping:** Should lessons be scoped per-project, per-agent, or global? Recommendation: per-project default with optional cross-project queries.

---

## Review Notes — Challenges to John's Output

### What I pushed back on:

1. **Original had "cross-agent real-time sync" as MVP.** Removed. This is a distributed systems problem that would delay launch by months. For MVP, agents share a local SQLite file or export/import JSON. Real-time sync is a v2 feature.

2. **Original included framework integrations in MVP.** Removed to out-of-scope. Building LangChain/CrewAI wrappers before the core SDK is solid is premature optimization. The raw SDK should be so simple that a 10-line wrapper is trivial for anyone to write.

3. **"Community lessons" kept creeping back in.** Killed it again. The product brief already flagged quality/trust as a major risk. MVP proves value with YOUR OWN agents sharing with EACH OTHER. Community comes much later.

4. **Success metrics were vanity-heavy.** Original had "10K GitHub stars" as a target. Revised to focus on repeat usage (30%+ weekly active) and PMF signal. Stars don't pay bills.

5. **Story 4 (prompt helper) was missing.** Added it. This is the bridge between "I have lessons" and "my agent actually uses them." Without this, developers have to figure out prompt injection themselves — friction that kills adoption.

6. **NF3 (install size) was missing.** Added 50MB cap. If `pip install lore-sdk` downloads 500MB of models, developers will bail. The embedded model choice is critical.

7. **"Would YOU use this?"** — Honestly, yes, but ONLY if it's truly zero-config. The moment I need to set up a server, configure a vector DB, or manage embeddings manually, I'd just use a JSON file. The bar is: simpler than a JSON file, smarter than a JSON file.
