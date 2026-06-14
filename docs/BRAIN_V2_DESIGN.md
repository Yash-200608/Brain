# Brain V2 — Design Document

> Status: PROPOSED · Date: 2026-06-12
> Scope: multi-user, multi-session, multi-agent, Jarvis-compatible, Chimera-compatible,
> mobile-node-compatible, local-first, cloud-optional.

---

## 0. Current State Assessment (what V2 builds on)

### What exists today

| Area | Implementation | File(s) |
|---|---|---|
| Cognitive loop | intent → retrieve → plan → execute w/ critic retry → reflect → log | `orchestrator/orchestrator.py` |
| Agents | Planner, Executor, Research, Critic, Memory, Extractor — sync Ollama wrappers | `agents/`, `memory/extractor.py` |
| Memory | One Chroma collection, hybrid scoring (semantic+keyword+importance+access+recency), reflection write-back, SQLite triple graph | `memory/` |
| Goals | SQLite store with subtasks, `COMPLETE_SUBTASK` instruction protocol | `goals/store.py` |
| Sessions | Append-only SQLite turn log | `logs/store.py` |
| API | FastAPI: `/api/query`, `/api/memory`, `/api/goals`, `/api/sessions`, `/health` | `api/` |
| Config | pydantic-settings + TOML + `JARVIS_` env | `config/config.py` |
| Deploy | docker-compose: api + ollama + nginx dashboard | `docker/` |

### Strengths to preserve (explicitly NOT redesigned)

1. **The cognitive loop itself.** Understand → Plan → Retrieve → Reason → Act → Learn is the product. V2 changes who can run it and how many can run at once — not what it does.
2. **Hybrid retrieval scoring** (`memory/retriever.py`). Tunable weighted blend with overshoot/rerank/dedupe/touch. Kept byte-for-byte; V2 only adds a scope pre-filter.
3. **Critic/retry loop** with confidence threshold. Kept as-is semantically.
4. **Risk-tiered tasks** (0 safe / 1 ask / 2 block). Kept and wired to a real approval channel.
5. **Reflection loop** (extract → score → write-back). Kept; gains consolidation jobs.
6. **Local-first stack**: Ollama + Chroma + SQLite. No mandatory cloud service in V2.
7. **Module taxonomy**. The directory map survives nearly unchanged.
8. **WorkerRegistry** — already the right extension point for multi-agent.
9. **Config system** — extended, not replaced.
10. **Existing REST surface** — preserved verbatim as the Jarvis compatibility layer.

### Gaps blocking the V2 goals

| Goal | Blocking gap |
|---|---|
| Multi-user | No identity concept. `AuthMiddleware` is a no-op. Memory collection, goals, sessions have no `user_id`. Rate limit is per-IP only. |
| Multi-session | One `SessionState` instance mutated under one global `RLock` (`orchestrator.py:60-67`); `session_id` overwrites shared state; module-level `_orch` singleton in `api/routes/query.py`. |
| Multi-agent | Sequential pipeline with `isinstance` dispatch (`orchestrator.py:118-146`); blocking `requests` calls; no agent↔agent messages; no streaming. |
| Jarvis compat | Exists (it IS the current API) — must not break. |
| Chimera compat | No protocol surface a second system can attach to beyond bare REST. |
| Mobile node | No sync protocol, no offline story, no delta feed. |
| Cloud-optional | No replication target, no remote-access story, LLM provider hard-coded to Ollama. |

---

## 1. Target Architecture

Three planes. Everything below the protocol plane is identical whether the caller
is Jarvis, Chimera, a mobile node, or the dashboard.

```
┌────────────────────────────  CLIENTS  ────────────────────────────┐
│  Jarvis (desktop/voice)   Chimera   Mobile nodes   Dashboard  CLI │
└──────────────┬──────────────┬───────────┬───────────┬─────────────┘
               │ REST /api/* (V1 compat)  │ REST v2    │ WS /v2/stream   │ MCP
┌──────────────▼──────────────▼───────────▼───────────▼─────────────┐
│  PROTOCOL PLANE (gateway)                                          │
│  auth: bearer key → Principal(user_id, client_id, scopes)          │
│  rate limit per principal · session routing · envelope (de)code    │
├────────────────────────────────────────────────────────────────────┤
│  COGNITIVE PLANE                                                   │
│  SessionManager ──▶ per-session SessionActor (serial mailbox)      │
│      each turn: IntentRouter → ContextBuilder → Planner            │
│                 → AgentRuntime (DAG, concurrent) → Critic loop     │
│                 → Reflector → episodic log                         │
│  EventBus (in-proc pub/sub): turn.*, task.*, memory.*, approval.*  │
├────────────────────────────────────────────────────────────────────┤
│  SERVICE PLANE                                                     │
│  MemoryService · GoalService · SessionService · IdentityService    │
│  ModelGateway (Ollama default; cloud LLM optional) · SyncService   │
├────────────────────────────────────────────────────────────────────┤
│  STORAGE                                                           │
│  Chroma (semantic, scoped metadata) · SQLite WAL (identity,        │
│  sessions, goals, graph, journal) · sync journal (append-only)     │
└────────────────────────────────────────────────────────────────────┘
        optional: cloud replica (journal subscriber) · Tailscale/relay
```

Four structural shifts — everything else is preserved:

1. **Singleton orchestrator → SessionManager + per-session actors.** Each session
   gets an actor with a serial mailbox (an `asyncio.Queue` + worker task). Turns
   within a session stay strictly ordered (same correctness property the global
   lock provides today); different sessions run concurrently. The actor holds
   `SessionState` (today's fields, unchanged) and is evicted to SQLite after idle
   timeout, rehydrated on demand.
2. **Principal threading.** `Principal {user_id, client_id, scopes}` is resolved
   at the gateway and passed down every call. Single-user installs get an implicit
   `owner` principal so the CLI and current Jarvis flows work with zero config.
3. **ModelGateway.** One async streaming interface (`generate(model, system,
   prompt, tools?) -> AsyncIterator[chunk]`) with an Ollama provider (default) and
   an optional cloud provider (Anthropic/OpenAI-compatible). Cloud is config, not
   architecture.
4. **EventBus.** In-process pub/sub. Everything observable (token chunks, task
   progress, memory writes, approval requests) is an event. WS streaming, the
   dashboard, the sync journal, and future remote agents are all just subscribers.

---

## 2. Module Boundaries

The V1 map survives. New modules are additive; renames are minimal.

| Module | Status | Responsibility (V2) |
|---|---|---|
| `core/` (was `orchestrator/`) | evolved | SessionManager, SessionActor, turn pipeline, DAG runner, critic loop. Depends only on service interfaces. |
| `identity/` | **new** | Users, clients, API keys, scopes. SQLite-backed. ~300 lines. |
| `sessions/` (absorbs `logs/`) | evolved | SessionState persistence, transcript/episodic log, idle eviction. |
| `memory/` | evolved | Tiers, scoping, MemoryService facade, retriever (unchanged scoring), extractor, graph, lifecycle jobs. |
| `agents/` | evolved | Agent protocol, manifests, registry/catalog, role agents. |
| `modelgw/` (was `models/`) | evolved | Provider interface; Ollama + optional cloud; embeddings, reranker, classifier live here too. |
| `protocols/` | **new** | Single source of truth for the wire: REST v2 schemas, WS envelope, MCP server, V1 compat shims. |
| `events/` | **new** | In-proc EventBus, event types. ~150 lines. |
| `sync/` | **new** | Append-only journal, delta-sync endpoints logic, replication client. |
| `goals/` | kept | Add `user_id` column; otherwise unchanged. |
| `reflection/` | kept | Unchanged semantics; consolidation job added. |
| `tools/` | kept | Tool layer; tools gain a manifest + risk class. |
| `config/` | kept | New sections; same mechanism. |
| `api/` | shrinks | Thin: route handlers call `protocols/` + `core/`. V1 routes preserved. |

**Dependency rules (enforced by import-linter in CI):**

- `protocols → core → {memory, goals, sessions, identity, modelgw} → storage`
- Agents touch memory **only** via `MemoryService` (never `ChromaMemoryStore` directly).
- `events/` and `config/` may be imported by anyone; they import nothing internal.
- Nothing imports `api/`; `api/` imports `protocols/`.
- This also fixes the V1 circular-import landmine documented in `memory/store.py:26-30`.

---

## 3. Communication Protocols

### 3.1 North–south (clients ↔ Brain)

**Envelope** — one JSON shape for WS frames, events, and agent messages:

```json
{ "v": 2, "type": "turn.token", "session": "s_...", "seq": 41,
  "ts": 1765500000.0, "payload": { } }
```

`v` is the protocol major; changes within a major are additive-only.

**Surfaces:**

| Surface | Path | Consumers | Notes |
|---|---|---|---|
| REST v1 (compat) | `/api/*` | Jarvis today | Preserved verbatim. Handlers alias to v2 with implicit `owner` principal. Golden-tested. |
| REST v2 | `/v2/turns`, `/v2/sessions`, `/v2/memory`, `/v2/goals`, `/v2/sync` | All clients | Principal-scoped, paginated, cursor-based. |
| WebSocket | `/v2/stream?session=` | Jarvis, Chimera, dashboard, mobile | Bidirectional envelopes: client sends `turn.submit`, `approval.grant`; server streams `turn.token`, `task.progress`, `turn.done`, `approval.request`, `memory.written`. |
| MCP server | stdio + streamable-HTTP | Claude, Chimera, any MCP client | Exposes `brain_query`, `memory_search`, `memory_write`, `goals_list`, `goals_update` as MCP tools. Cheapest possible interop layer — any MCP-capable agent can mount the Brain as a tool server with zero custom client code. |

**Auth:** `Authorization: Bearer <key>` → `Principal`. Scopes: `query`,
`memory.read`, `memory.write`, `goals`, `sync`, `admin`. Keys are per-client
(Jarvis key, Chimera key, each mobile node its own key) so revocation is
per-device. Localhost CLI bypass = implicit owner principal (config flag,
default on, off in server mode).

### 3.2 East–west (agent ↔ agent)

Typed messages on the EventBus, same envelope: `task.assign`, `task.progress`,
`task.result`, `task.failed`, `memory.event`. In-process only in V2.0 — but
because the wire shape equals the WS shape, a `remote` agent later is just a
registry entry whose mailbox is a WS connection instead of a queue. No redesign.

### 3.3 Mobile sync protocol

Pull-based delta sync over REST — boring on purpose:

- `GET /v2/sync?cursor=<ulid>&scope=memory,goals` → ordered journal entries since cursor.
- `POST /v2/sync` → batch of client-originated ops (each with a client-generated ULID; idempotent, dedup on ULID).
- Conflict rule: **last-writer-wins per item + tombstones**. Memories are
  append-mostly facts; true concurrent edits to one item are rare. CRDTs are
  explicitly out of scope — revisit only if real conflicts show up.

### 3.4 Compatibility contracts

- **Jarvis:** the contract is the existing `/api/*` surface + response shape of
  `orchestrator.handle()` (`session_id`, `response`, `memory_used`, `tasks`).
  Frozen, golden-tested in CI from Phase 0.
- **Chimera:** *assumption — Chimera integrates over the protocol plane (REST v2 /
  WS / MCP), not by importing Brain code.* Three integration modes supported:
  (a) Chimera as a **client** (calls `/v2/turns`), (b) Chimera as a **tool user**
  (mounts Brain via MCP), (c) Chimera agents as **remote workers** (Phase 4+,
  `task.assign` over WS). If Chimera needs in-process embedding instead, that's a
  scope change to flag before Phase 4.

---

## 4. Memory Architecture

Five tiers — four already exist in embryonic form; V2 formalizes them and adds
scoping + a sync journal. **The retrieval scoring function does not change.**

| Tier | Contents | Store | V1 ancestor |
|---|---|---|---|
| Working | Current-session history + retrieved context | RAM (SessionActor), snapshot to SQLite on evict | `SessionState` |
| Episodic | Every turn (input, response, tasks, memory_used) | SQLite `turns` | `logs/store.py` |
| Semantic | Durable facts, embedded | Chroma `jarvis_memory` | `memory/store.py` |
| Procedural | Reflection insights, "how to" knowledge | Chroma, `kind=insight` | `source=reflection` metadata |
| Graph | (subject, relation, object) triples | SQLite `edges` | `memory/graph_builder.py` |

### Scoping

Single Chroma collection with metadata filtering (NOT per-user collections — one
embedding space, simple migration, Chroma `where` filters are sufficient at this
scale). Every memory item gains:

```python
{
  "user_id": str,            # owner principal
  "visibility": "private" | "shared" | "global",
  "session_id": str | None,  # provenance
  "agent_id": str | None,    # which agent wrote it
  "kind": "fact" | "insight" | "preference" | "event",
  "source": str,             # reflection | explicit | sync | ...
  "origin_node": str,        # for sync provenance
  "pinned": bool,
}
```

Retrieval pre-filter: `user_id == principal.user_id OR visibility in (shared, global)`,
applied as a Chroma `where` clause **before** the existing overshoot/score/dedupe
pipeline. Scoring weights, touch semantics, recency half-life: unchanged.

### Write path & journal

All writes go through `MemoryService.write()`, which (1) writes Chroma/SQLite and
(2) appends to the **journal**:

```sql
CREATE TABLE journal (
  id TEXT PRIMARY KEY,        -- ULID, globally ordered
  op TEXT NOT NULL,           -- memory.add | memory.update | memory.delete | goal.upsert | ...
  user_id TEXT NOT NULL,
  payload TEXT NOT NULL,      -- JSON
  origin_node TEXT NOT NULL,
  ts REAL NOT NULL
);
```

The journal is the universal feed: mobile delta sync reads it, the optional cloud
replica subscribes to it, and it doubles as an audit log.

### Lifecycle (background jobs, all idempotent)

- **Decay:** importance × e^(−age/τ) recomputed weekly; sub-threshold unpinned items archived.
- **Consolidation:** reflection-written near-duplicates merged (embedding-similarity clusters → one canonical fact, weight summed).
- **TTL:** `kind=event` items expire by default; facts/preferences don't.

### Migration of existing data

One script: backfill `user_id=owner`, `visibility=private`, `kind` inferred from
`source`; emit genesis journal entries; add `user_id` columns to goals/sessions/graph
SQLite tables (nullable → backfilled → NOT NULL). Reversible (columns are additive;
Chroma metadata is additive).

---

## 5. Agent Architecture

Kept: registry, the five roles, risk levels, critic semantics, planner-emits-JSON-steps.

### 5.1 Uniform protocol (deletes the isinstance ladder)

```python
class AgentResult(TypedDict):
    output: str
    artifacts: dict
    memory_suggestions: list[dict]

class BrainAgent(Protocol):
    manifest: AgentManifest
    async def run(self, task: Task, ctx: TurnContext) -> AgentResult: ...
```

`TurnContext` carries: `principal`, `session_id`, `memory: MemoryService` (scoped),
`models: ModelGateway`, `emit: Callable[[Event], None]`, `working_context: str`.
The special-casing in `orchestrator.py:131-137` collapses into each agent's `run()`.

### 5.2 Manifests → dynamic planner catalog

```python
@dataclass
class AgentManifest:
    name: str; description: str
    model: str                 # config-resolved
    tools: list[str]
    max_risk: int              # highest risk this agent may execute
    cost: Literal["low", "med", "high"]
    kind: Literal["local", "remote"] = "local"
```

The planner prompt is built from the registry catalog at call time — registering a
new agent (including a future remote Chimera worker) makes it plannable with **no
prompt edits**.

### 5.3 Plans become DAGs

`Task` gains `id` (it has one) + `depends_on: list[str]` (default `[]`). The
runner executes all ready tasks concurrently (per-session cap, default 3),
feeding completed outputs into dependents' context. A V1 sequential plan is the
degenerate chain case — existing planner output remains valid, zero behavior
change until the planner starts emitting parallel branches.

### 5.4 Tools

`tools/` stays. Tools gain a manifest (name, schema, risk class). Agents may only
call tools listed in their manifest. Where the local model supports native tool
calling (Ollama tools API), use it; otherwise fall back to the current
JSON-extraction approach. Same `Task.risk` gates apply to tool invocations.

### 5.5 Risk & approval (upgrade of the silent block)

- risk 0 → execute.
- risk 1 → emit `approval.request` event; actor parks the task; client (Jarvis UI,
  mobile push, dashboard) answers with `approval.grant|deny`; timeout = deny.
  (V1 silently executed risk-1 — this closes that gap.)
- risk 2 → blocked, as today.
- `principal.scopes` caps the maximum risk any plan may contain for that client.

### 5.6 Remote agents (Phase 4+, design now, build later)

`kind: remote` registry entries hold a WS endpoint + auth key. The DAG runner
sends `task.assign` envelopes and awaits `task.result` with timeout/retry. This is
the Chimera-as-worker and mobile-node-as-sensor path. Nothing in the core changes
when it lands — that's the point of the shared envelope.

---

## 6. Deployment Architecture

### Topologies (each a superset of the previous; all optional beyond the first)

**T1 — Local-first single node (default; preserves today exactly):**
```
docker-compose: brain-api · ollama · dashboard(nginx)
volumes: ./data (SQLite WAL + Chroma + journal)
also: bare `python main.py cli|api`
```

**T2 — LAN hub:** same image on a home server; Jarvis desktop, mobile nodes,
Chimera connect over LAN. TLS via Caddy sidecar (compose profile `tls`).
Remote access: **Tailscale recommended over a custom relay** — zero Brain code,
encrypted, free tier suffices.

**T3 — Cloud-optional add-ons (independent toggles):**
- **Cloud replica:** same container in a VPS, runs `sync/` in subscriber mode
  against the home node's journal. Serves reads / acts as warm standby. Promotion
  is manual in V2 (documented runbook, not automated failover).
- **Hosted LLM fallback:** ModelGateway config — `provider=anthropic` for the
  planner/critic on hard queries, Ollama for everything else. Per-model routing
  in `settings.toml`.
- **Relay:** only if Tailscale is unacceptable; a stateless WS proxy, no storage.

**Mobile node:** thin client (not a full Brain): local SQLite cache (recent
episodic + pinned/high-importance semantic working set), offline write queue,
delta sync on reconnect, WS stream when live. Reference implementation as a
library (`brainlink`) so Jarvis-mobile/Chimera-mobile embed it.

### Process model

One `brain-api` process, asyncio, `uvicorn --workers 1` — **deliberate**: the
EventBus and SessionActors are in-process. Concurrency comes from async I/O (LLM
calls dominate latency; the GIL is irrelevant while awaiting Ollama). Embedding
encode is offloaded to a small thread pool. If one box ever isn't enough,
the scale-out path is sticky-session routing by `session_id` — documented, not built.

### Storage & ops

- SQLite in WAL mode (one `PRAGMA`, Phase 0) — concurrent readers + single writer
  is exactly the actor model's write pattern.
- Backup: nightly `brainctl backup` → journal snapshot + SQLite `.backup` + Chroma
  dir tar. `brainctl export/import` for full-fidelity moves.
- Observability: structured JSON logs (exists in embryo), `/v2/metrics`
  (Prometheus text format: turns/min, p95 turn latency, critic retry rate,
  memory size, journal lag per sync client).

---

## 7. Migration Plan — Current Brain → V2

Principles: ship in phases, each independently releasable; `/api/*` never breaks;
single-user UX never regresses; no big-bang rewrite.

### Explicit non-goals (do NOT build)

- No microservices, no Kubernetes, no message broker (Redis/NATS) — in-proc bus only.
- No Postgres by default (SQLite WAL is correct for the actor write pattern; a
  repository seam exists if a cloud replica ever wants Postgres).
- No CRDTs (LWW + tombstones).
- No changes to retrieval scoring, critic semantics, or the reflection concept.
- No automated cloud failover in V2.

### Phase 0 — Safety net (Weeks 1–2)
- Golden tests freezing `/api/query` request/response behavior (use existing pytest suite as base).
- `PRAGMA journal_mode=WAL` on all SQLite stores.
- import-linter contract for current dependency graph (locks in boundaries before refactor).
- **Exit:** CI red if V1 surface changes.

### Phase 1 — Multi-session core (Months 1–2)
- `core/`: SessionManager + SessionActor (asyncio); delete global RLock + singleton `_orch`.
- `sessions/`: state snapshot/rehydrate on top of existing `sessions.db`.
- `Agent.call` → async (`httpx`), streaming-capable; ModelGateway introduced (Ollama provider only).
- CLI + `/api/query` unchanged externally.
- **Exit:** two concurrent sessions interleave correctly under load test; goldens green.

### Phase 2 — Identity & scoping (Months 2–3)
- `identity/` module; real AuthMiddleware (bearer keys); per-principal rate limits (extend existing token-bucket).
- Principal threading through core + services.
- Memory metadata backfill script; scoped retrieval pre-filter; `user_id` on goals/sessions/graph.
- Implicit `owner` principal for CLI/localhost → single-user UX identical.
- **Exit:** two users on one Brain cannot read each other's private memory (tested); goldens green.

### Phase 3 — Agent runtime v2 + events (Months 3–5)
- `BrainAgent` protocol + manifests; port the five role agents; delete isinstance dispatch.
- Task DAG runner (sequential plans still work); EventBus; approval flow for risk-1.
- WS `/v2/stream` with token streaming + task progress.
- Dashboard upgraded to consume WS (replaces polling).
- **Exit:** a plan with two parallel research branches executes concurrently; Jarvis streams tokens.

### Phase 4 — Protocol surface (Months 5–7)
- REST v2 routes; `/api/*` reduced to compat shims over v2.
- MCP server exposure (brain_query, memory_search/write, goals).
- Chimera integration tests against REST v2 + WS + MCP (modes a/b from §3.4); remote-agent envelope spec finalized (implementation may slip to Phase 6).
- **Exit:** an MCP client (e.g. Claude Code) can mount the Brain and search/write memory; Chimera talks to v2 in CI.

### Phase 5 — Sync & mobile (Months 7–9)
- `sync/`: journal (backfilled from Phase 2 genesis entries), `GET/POST /v2/sync`, cursor semantics, tombstones.
- `brainlink` client library: local cache, offline queue, reconnect/replay.
- Per-device API keys + revocation.
- **Exit:** mobile node works offline for a day, reconnects, converges with no data loss (chaos-tested with simulated 3-device divergence).

### Phase 6 — Cloud-optional & hardening (Months 9–12)
- Cloud replica mode (journal subscriber) + promotion runbook; Tailscale docs; optional relay.
- Hosted-LLM provider in ModelGateway with per-model routing.
- Memory lifecycle jobs (decay, consolidation, TTL).
- Security pass: TLS profile, key rotation, CORS tightening (kill `allow_origins=["*"]`), scope audit.
- Observability: metrics endpoint, journal-lag alerting.
- **Exit:** kill the home node → replica serves reads; restore → journal catches up. V2.0 tagged.

### Risk register

| Risk | Mitigation |
|---|---|
| Async refactor destabilizes the loop (Phase 1 is the riskiest) | Goldens from Phase 0; actor model preserves per-session serialization, so V1's correctness argument carries over |
| Chimera's actual interface differs from assumption §3.4 | Three integration modes offered; verify assumption before Phase 4 starts — only `protocols/` is affected either way |
| Local models too weak for DAG planning | DAG is optional output; sequential plans remain valid; hosted-LLM fallback for planner only |
| Sync conflicts worse than expected | Journal is append-only — conflict policy is swappable without storage changes |
| SQLite write contention at higher user counts | WAL + single-writer actor pattern; repository seam to Postgres exists if ever needed |

### Effort summary

| Phase | Window | Theme |
|---|---|---|
| 0 | Wks 1–2 | Freeze contracts |
| 1 | Mo 1–2 | Multi-session |
| 2 | Mo 2–3 | Multi-user |
| 3 | Mo 3–5 | Multi-agent + streaming |
| 4 | Mo 5–7 | Jarvis/Chimera/MCP protocol surface |
| 5 | Mo 7–9 | Mobile sync |
| 6 | Mo 9–12 | Cloud-optional + hardening → V2.0 |
