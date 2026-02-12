# Phase 2 Product Brief — Lore Cloud & Org-Wide Sharing

**Author:** Paige (Product Strategist) | **Date:** 2026-02-12
**Status:** Draft — reviewed and challenged
**Depends on:** [Phase 1 Product Brief](./product-brief.md)

---

## 1. What Phase 2 Unlocks

Phase 1 (shipped, v0.1.1) proved the SDK works locally. But local-only has hard limits:

| Local-only limitation | What cloud solves |
|---|---|
| Agent A learns something on machine X, Agent B on machine Y never knows | Shared lesson store — all agents read/write the same pool |
| New agent starts cold — zero knowledge | New agents inherit the org's accumulated wisdom from day one |
| Team member's lessons die on their laptop | Centralized, persistent, backed-up |
| No visibility into what agents are learning | Analytics: which lessons get used, which are stale |
| Redaction matters less when it's your own disk | Redaction becomes critical when sharing across people/machines |

**The honest "so what" test:** If Lore Cloud is just "SQLite but on a server," it's not worth building. The value must come from **cross-agent knowledge transfer that's impossible locally** — specifically:
1. Agents on different machines/teams share lessons without manual export/import
2. New agents bootstrap with org knowledge instantly
3. The redaction layer enforces org-wide data hygiene automatically
4. **MCP support makes this zero-code agent memory** — any MCP-compatible agent (Claude Desktop, OpenClaw, OpenAI agents) gets Lore as a tool with zero code changes. The agent decides when to save and recall lessons. This changes the pitch from "SDK you integrate" to "tool your agents just use"

---

## 2. Competitive Positioning Update

### Mem0 (raised $5M+, growing)
- Still focused on **user/conversation memory** ("remember John likes dark mode")
- Added "organization memory" feature but it's user-preference scoped
- **No MCP support.** This is a significant gap — Mem0 requires SDK integration, Lore works as a tool agents just use.
- **Risk:** They could pivot to operational lessons. But their data model and API are conversation-centric. Pivoting would be a near-rewrite.
- **Our play:** Don't compete on user memory. Double down on **operational/agent lessons** — different schema, different query patterns, different value prop. MCP gives us a distribution advantage: any MCP-compatible agent is a potential user with zero integration work.

### LangMem (LangChain)
- Tightly coupled to LangChain ecosystem
- No cross-agent sharing, no redaction
- **Our play:** Framework-agnostic. Works with LangChain AND everything else.

### "Just use Postgres with an API"
This is the real competitor. Honest answer:
- Yes, you COULD store lessons in Postgres with a REST API
- What you'd still need to build: embedding + hybrid search, redaction pipeline, confidence decay, prompt formatting, SDK clients, org/team scoping, API key management
- **And you definitely wouldn't get MCP integration** — Lore as an MCP server means any agent gets memory as a tool with zero code. Try doing that with raw Postgres.
- **Lore's value = all of that pre-built, tested, and opinionated**
- The moat is thin here. Speed to value and developer experience ARE the moat.

### What's our actual moat?
1. **Redaction is hard to DIY** — our 6-layer pipeline (expanding to LLM-powered in cloud) is real IP
2. **Lesson schema + decay model** — not just "store and retrieve" but lessons that age, get voted on, expire
3. **SDK-first + MCP-native** — competitors are APIs you integrate. We're a library that just works, with optional cloud, AND an MCP server that gives agents memory as a tool with zero code
4. **Open source core** — lock-in resistance that Mem0 (closed) can't match
5. **Zero-code via MCP** — the agent decides when to save/recall. No developer instrumentation. This is a fundamentally different integration model that no competitor offers.

**Honest assessment: moat is narrow.** We're betting on execution speed and developer love, not technical barriers. If Mem0 ships cross-agent operational memory with redaction, we're in trouble.

---

## 3. Self-Hosted vs Managed vs Both

**Recommendation: Both, but ship self-hosted first.**

| Option | Pros | Cons |
|---|---|---|
| Self-hosted only | Zero infra cost for Amit, appeals to privacy-sensitive | No recurring revenue, support burden |
| Managed only | Revenue from day 1, simpler ops | Lock-in concern for OSS users, infra cost |
| **Both** | Best of both worlds | Two things to maintain |

**Sequencing:**
1. **Week 1-2:** Self-hosted server (Docker image, single binary). This IS the MVP.
2. **Week 3+:** Deploy same server as managed service on fly.io/Railway
3. **Later:** Managed gets premium features (LLM redaction, analytics, SLA)

The self-hosted server IS the managed server — same codebase, just different deployment. This isn't two products.

---

## 4. Community Sharing: Not Yet

**Verdict: Too early. Skip for Phase 2.**

Reasons:
- Need 50+ orgs using cloud before community has content worth sharing
- Curation/quality is unsolved — who decides if a lesson is good?
- Legal/liability questions (what if a community lesson causes harm?)
- Solo dev can't moderate a community

**When to revisit:** When 100+ orgs are on cloud and organically asking to share lessons across org boundaries.

---

## 5. Pricing Model for Cloud Tier

| Tier | Price | Includes |
|---|---|---|
| **Free** | $0 | 1 org, 3 API keys, 1K lessons, basic redaction |
| **Team** | $29/mo | 1 org, 10 API keys, 25K lessons, team scoping |
| **Pro** | $99/mo | 3 orgs, unlimited keys, 100K lessons, LLM redaction, analytics |

**Changes from Phase 1 brief:**
- Lowered Team from $49 to $29 — reduce friction for early adopters
- Simplified tiers — no enterprise tier yet (solo dev, remember?)
- Metered by lessons stored, not agents (agents are hard to count)

**Revenue math:** 100 teams × $29 = $2,900 MRR. 50 Pro × $99 = $4,950 MRR. Combined ~$8K MRR is realistic 6-month target. Not life-changing but validates the model.

---

## 6. Risk Assessment

| Risk | Severity | Mitigation |
|---|---|---|
| Building a server stretches solo dev too thin | HIGH | Keep server dead simple. FastAPI + Postgres. No microservices. |
| Cloud adds security surface (data breaches, auth bugs) | HIGH | Use established patterns: API keys with hashing, per-org DB isolation |
| Users expect uptime Amit can't guarantee | MEDIUM | Self-hosted as primary, managed as "best effort" for now |
| "Just use Postgres" objection gets louder with a server | HIGH | SDK remains the product. Server is the enabler, not the value. |
| Hybrid sync (local+remote) is complex | MEDIUM | MVP: remote only. Hybrid is a separate phase. |

---

## Review Notes — Challenges to Paige's Phase 2 Output

### What I pushed back on:

1. **Original included community sharing in Phase 2.** Killed it. Amit has zero capacity to moderate a community. The product doesn't have enough users to make community content valuable. This is a Phase 4 thing at earliest.

2. **Original pricing was too high.** $49/mo for a Team tier of an unproven v2 product from a solo dev? Dropped to $29. The goal is adoption, not revenue optimization.

3. **"Moat" section was hand-wavy.** Forced an honest assessment. The moat IS narrow. That's not fatal — many successful dev tools have thin moats (Stripe's moat is DX, not technology). But we need to be honest about it.

4. **Is this actually differentiated from "a database with an API"?** Barely, at the infrastructure level. The differentiation is in the SDK (zero-config, embeds + hybrid search built in), the redaction pipeline (no one else does this), and the lesson lifecycle (decay, voting, expiry). If we strip those, yes, it's just Postgres with a REST API. Don't strip those.

5. **Hybrid sync was in MVP scope.** Pulled it out. Local cache + remote sync is a distributed systems problem (conflict resolution, eventual consistency, offline queues). That's a month of work alone. MVP is pure remote — the RemoteStore replaces SqliteStore, no syncing.
