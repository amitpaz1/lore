# Product Brief — Cross-Agent Memory Sharing Platform

**Author:** Paige (Product Strategist) | **Date:** 2026-02-12
**Status:** Draft — reviewed and challenged (see Review Notes at bottom)

---

## 1. Product Name Candidates

| Name | Rationale | Risk |
|------|-----------|------|
| **Hive** | Collective intelligence, short, memorable | Generic, hard to SEO |
| **Engram** | Neuroscience term for a memory trace | Nerdy, not immediately clear |
| **Hivemind SDK** | Descriptive + evocative | "Hivemind" overused in tech |
| **Recall** | Simple, verb-based, developer-friendly | Common word, trademark risk |
| **Synapse** | Neural connection metaphor | Already used by Microsoft (Azure Synapse) |
| **Lore** | "Accumulated knowledge/wisdom" | Short, memorable, `.dev` likely available |

**Recommendation: Lore** — it's short, evocative ("agent lore"), works as a brand (`lore.dev`, `@loredev`), and the metaphor is intuitive: agents accumulate and share lore.

Runner-up: **Engram** — more technical, appeals to ML crowd.

---

## 2. Vision & Mission

**Vision:** Every AI agent gets smarter from the collective experience of all agents before it.

**Mission:** Provide the simplest possible SDK for agents to publish operational lessons and query lessons from other agents — with privacy-safe redaction built in, not bolted on.

---

## 3. Target Market & Personas

### Who needs this TODAY (not theoretically)

**Primary: Teams running multiple AI agents in production (10+ agents)**
- They already have agents failing, retrying, hitting the same edge cases
- Pain: Agent A discovers an API returns 429 after 50 req/min. Agent B hits the same wall tomorrow. No learning transfer.
- Size: Small but real. Companies like Adept, Cognition (Devin), multi-agent SaaS builders.
- **Honest assessment:** This is maybe 500-2,000 teams worldwide right now. Growing fast but small today.

**Secondary: AI agent framework authors (LangChain, CrewAI, AutoGen, etc.)**
- They want to offer "memory" as a feature but don't want to build it
- Integration play: Lore becomes the memory layer these frameworks recommend
- **Honest assessment:** Hard to get framework buy-in. They'd rather build their own.

**Tertiary: Solo developers building agents who want "smarts out of the box"**
- "I pip install lore and my agent starts with knowledge from the community"
- **Honest assessment:** Cool vision but trust/quality problems. Who curates the community knowledge?

### Who does NOT need this (avoid these)
- Enterprise "knowledge management" buyers (too vague, wrong buyer)
- RAG-focused teams (they want document retrieval, not operational lessons)
- Teams with 1-2 agents (no cross-agent value)

---

## 4. Competitive Landscape

| Product | What it does | How Lore differs |
|---------|-------------|-----------------|
| **Mem0** | Per-user memory for AI apps (remembers user preferences) | Mem0 = user memory. Lore = operational/agent memory. Different problem. |
| **LangMem (LangChain)** | Long-term memory within LangChain agents | Locked to LangChain. Single-agent focus. No cross-agent sharing. |
| **Zep** | Memory server for AI assistants | Conversation memory, not operational lessons. User-centric. |
| **Vector DBs (Pinecone, Weaviate, Qdrant)** | Raw similarity search | Infrastructure, not product. You still need the lesson schema, redaction, curation. |
| **Custom RAG pipelines** | DIY knowledge bases | Everyone builds their own, poorly. Lore is the "don't build this yourself" option. |

### Honest gap analysis
The hard truth: **Mem0 is the closest competitor and they have funding and traction.** But Mem0 focuses on user/conversation memory ("remember that John likes dark mode"). Lore focuses on operational agent knowledge ("this API rate-limits at 50/min", "GPT-4 hallucinates on date math, use a tool instead"). These are genuinely different use cases.

The **real competitor is "just use a vector DB."** Our answer must be: Lore gives you schema, redaction, curation, and cross-agent sharing that you'd spend weeks building on top of a vector DB.

---

## 5. Unique Differentiators

1. **Cross-agent by default** — Not "memory for one agent" but "shared lessons across agents." This is the key insight from AgentLens.
2. **Redaction built-in** — 6-layer pipeline strips PII/secrets before sharing. No other memory product does this.
3. **Operational lessons, not conversation memory** — Different data model. Lessons have: context, problem, resolution, confidence, staleness.
4. **Community/marketplace potential** — Public lessons that any agent can query. "npm for agent wisdom."
5. **Framework-agnostic** — Works with LangChain, CrewAI, raw OpenAI, whatever.

---

## 6. Business Model & Pricing

### Open-core model (recommended)

**Open source (free forever):**
- Core SDK (publish + query lessons)
- Local storage backend (SQLite + embeddings)
- Basic redaction (regex-based PII stripping)
- Self-hosted server option

**Cloud hosted (paid):**
- Managed Lore server (no infra to run)
- Advanced redaction (LLM-powered, 6-layer)
- Cross-team sharing (your org's agents share with each other)
- Community lessons access (curated public knowledge base)
- Analytics (which lessons get used, which agents learn fastest)

**Pricing (grounded in reality):**
| Tier | Price | Target |
|------|-------|--------|
| **Free** | $0 | Solo devs, OSS, evaluation |
| **Team** | $49/mo | Small teams, up to 10 agents, 10K lessons stored |
| **Pro** | $199/mo | Larger teams, unlimited agents, advanced redaction, community access |
| **Enterprise** | Custom | SSO, audit logs, on-prem, dedicated support |

**Why these numbers:** Mem0 charges ~$99/mo for their pro tier. We're positioning slightly below for Team (simpler product) and comparable for Pro. The free tier is critical — developer adoption requires zero friction.

**Revenue reality check:** At $49-199/mo, you need ~500 paying teams for $50K MRR. That's achievable in 12-18 months IF the product is genuinely useful AND the market grows as expected. This is a bet on the multi-agent future.

---

## 7. Go-to-Market

### Phase 1: Open-source SDK launch (Month 1-2)
- Ship Python + TypeScript SDKs on PyPI/npm
- README with 5-line quickstart
- Blog post: "Why your agents keep making the same mistakes"
- Post on HN, Reddit r/MachineLearning, AI Twitter
- Target: 500 GitHub stars, 100 weekly active SDK users

### Phase 2: Cloud beta (Month 3-4)
- Launch hosted version with free tier
- Integrations: LangChain, CrewAI, OpenAI Assistants
- Target: 50 teams on cloud, 10 paying

### Phase 3: Community lessons (Month 5-6)
- Public lesson marketplace
- Curated "starter packs" (web scraping lessons, API integration lessons, etc.)
- Target: 1,000 public lessons contributed

### Channel strategy
- **Primary:** Developer content (blog, Twitter, HN, Discord)
- **Secondary:** Framework partnerships (get listed in LangChain/CrewAI docs)
- **NOT:** Enterprise sales, conferences, paid ads (too early, too expensive)

---

## 8. Risks & Honest Assessment

### Is the market ready?

**Partially.** Multi-agent systems are real but early. Most teams are still running 1-3 agents. The "dozens of agents sharing knowledge" scenario is 12-18 months away for most. However:
- Early movers (Devin-style coding agents, customer support agent fleets) need this NOW
- Being early lets you shape the category
- The OSS play means even if the market is slow, you build mindshare

### Key risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Market too early — not enough multi-agent teams | HIGH | Open-source hedges this. Even single-agent memory is useful. |
| "Just use a vector DB" objection | HIGH | Must prove the schema/redaction/curation layer saves real time. |
| Mem0 adds cross-agent features | MEDIUM | They're focused on user memory. Different DNA. But watch them. |
| Quality of community lessons is garbage | MEDIUM | Curation + voting + confidence scores. Don't launch community too early. |
| Solo dev (Amit) can't maintain OSS + cloud + support | HIGH | Keep MVP ruthlessly small. Cloud can wait. SDK first. |
| Lesson staleness — old lessons become wrong | MEDIUM | Built-in TTL, confidence decay, version tagging. |

### Timing verdict
**6/10 — Proceed with caution.** The market is real but early. The open-source approach de-risks timing because you build adoption even before monetization. The biggest risk is spreading too thin. Ship the SDK, prove it's useful for 2-3 real teams, then decide on cloud.

---

## Review Notes — Challenges to Paige's Output

### What I pushed back on:

1. **"Community marketplace" is premature.** Original draft had this as a core feature. Moved it to Phase 3 and flagged quality risk. Nobody will trust random community-sourced agent lessons without serious curation. This is a nice-to-have, not a differentiator for launch.

2. **Persona #3 (solo devs wanting community knowledge) is aspirational, not real.** Kept it as tertiary but honest about it. The "npm for agent wisdom" analogy is seductive but the trust/quality problem is massive. You don't pip-install random operational advice.

3. **Enterprise tier pricing is premature.** Removed specific enterprise pricing. Amit is a solo dev. Don't pretend you're selling to enterprises in Month 1.

4. **"Framework-agnostic" is a feature, not a differentiator.** Every new tool claims this. The real differentiator is redaction + cross-agent sharing. Kept it in the list but deprioritized.

5. **Revenue projections were optimistic.** Original had $100K MRR in 12 months. Revised to $50K in 12-18 months, which is still optimistic for a solo dev in an early market.

6. **Name "Hive" was original top pick.** Pushed back — too generic, impossible to SEO, and "hive mind" has negative connotations (Borg, loss of individuality). Switched recommendation to "Lore."
