# Brain V2 Foundation — Implementation & Migration Notes

> Status: IMPLEMENTED · Date: 2026-06-12
> Companion to [BRAIN_V2_DESIGN.md](BRAIN_V2_DESIGN.md). This document records what
> was actually built in the foundation pass, what is guaranteed to keep working,
> and how to extend from here.

Brain is the authoritative central server. Jarvis, Chimera and mobile nodes are
clients. Everything below exists to make that fact structural.

---

## 1. What was built

| Priority | Deliverable | Where |
|---|---|---|
| 1 | SessionManager → SessionActor → CognitivePipeline | `core/manager.py`, `core/session.py`, `core/pipeline.py` |
| 1 | Backward-compatible facade | `orchestrator/orchestrator.py` (rewritten as facade) |
| 2 | Principal + IdentityService (non-enforcing) | `identity/` |
| 3 | Versioned Envelope protocol | `protocols/` |
| 4 | Async-compatible typed EventBus | `events/` |
| 5 | AgentProtocol + AgentResult, agents migrated | `agents/protocol.py`, `agents/base.py`, role agents |
| 6 | MemoryService / SessionService / GoalService | `services/` |
| 7 | Memory scoping metadata foundation | `memory/scoping.py`, `services/memory_service.py` |
| 8 | ModelGateway (Ollama default) | `modelgw/` |

### Dependency direction (enforced by construction)

```
api  →  orchestrator (facade)  →  core  →  agents / services  →  storage
                                   ↘  events, identity, protocols, modelgw (leaf packages)
```

`core.context`, `core.task`, `protocols`, `events`, `identity`, `modelgw` import
nothing from the layers above them. Agents reference `core.context` /
`core.task` types via `TYPE_CHECKING` only, which also removes the V1
circular-import landmine documented in `memory/store.py`.

### Module moves (shims left behind — old imports keep working)

| Old path | New home |
|---|---|
| `orchestrator.task` | `core.task` |
| `orchestrator.planner` | `core.planning` |
| `orchestrator.router` | `core.routing` |
| `orchestrator.context_optimizer` | `core.context_optimizer` |

---

## 2. The session architecture

V1 had one `SessionState` behind one global `RLock`: one conversation at a
time, and passing a `session_id` silently overwrote shared state. V2:

- **`SessionManager`** owns a table of actors, creates them on demand, and
  evicts the longest-idle, non-busy actors past `settings.max_sessions`
  (default 256). Eviction releases in-RAM working state only — the episodic
  turn log persists, exactly what a V1 process restart already implied.
- **`SessionActor`** owns one session's `SessionState` and a per-session lock:
  turns within a session are serialized (V1's correctness property, kept),
  while distinct sessions run concurrently (V1's bottleneck, removed).
- **`CognitivePipeline`** is the V1 turn logic, behavior-identical, async-defined.
  Agents execute via `await agent.run(task, ctx)`; blocking LLM/DB work is
  offloaded with `asyncio.to_thread`.

Sync callers (CLI, threadpool-backed FastAPI routes) use
`actor.handle_turn(...)`, which bridges with `asyncio.run` on a private loop.
Async callers use `await actor.ahandle_turn(...)`. Both serialize on the same
lock, so the modes can coexist.

### The facade

`JarvisOrchestrator` keeps its V1 surface byte-for-byte: constructor signature,
all public attributes (`memory_store`, `memory_agent`, `registry`, `router`,
`planner`, `critic`, `context_opt`, `reflector`, `goal_store`, `log_store`,
`state`), `handle(user_input, session_id=None)` and the response dict shape
`{session_id, response, memory_used, tasks}`. V1's session *stickiness*
(an explicit `session_id` stays current for later calls that omit one) is
reproduced in the facade — and only in the facade. New code should use
`SessionManager` directly.

---

## 3. New contracts

### Envelope (`protocols`) — protocol version 2

```json
{ "version": 2, "type": "turn.completed", "session": "s_…",
  "sequence": 41, "timestamp": 1781234567.0, "payload": { } }
```

Rules: additive-only within a major version; receivers ignore unknown fields
(enforced via pydantic `extra="ignore"`) and unknown types. Canonical type
names live in `protocols.EnvelopeType`. This is the future wire contract for
Jarvis, Chimera and mobile nodes — WebSocket frames, sync feeds and remote
agent messages all reuse this one shape.

### Events (`events`)

`EventBus.subscribe(type | "*", handler)` / `publish` (sync-safe) /
`apublish` (awaits async handlers). Handler errors are logged and isolated —
the bus can never break a turn. Typed events cover turn lifecycle
(`TurnStarted/TokenStreamed/TurnCompleted`), task lifecycle
(`TaskStarted/Completed/Failed/Blocked`), `MemoryWritten`,
`ApprovalRequested`, `AgentEvent`; every event converts to an `Envelope` via
`to_envelope()`. Currently emitted: turn + task lifecycle (pipeline) and
memory writes (MemoryService). Token streaming and approvals are defined but
not yet wired — that is deliberate foundation scope.

### Principal (`identity`)

`Principal(user_id, client_id, scopes, metadata)` with scope constants
(`query`, `memory.read`, `memory.write`, `goals`, `sessions`, `admin`).
`IdentityService.resolve(token)` maps bearer keys (from
`settings.api_keys` / `JARVIS_API_KEYS`, `token → user_id`) to principals;
`default_principal()` is the owner with all scopes. **Nothing is enforced
yet**: `AuthMiddleware` resolves and attaches `request.state.principal`,
falling back to owner, and never rejects. Single-user operation is untouched.

### AgentProtocol (`agents.protocol`)

```python
class AgentProtocol(Protocol):
    name: str
    async def run(self, task: Task, context: TurnContext) -> AgentResult: ...
```

`AgentResult(status, output, metadata, events)`. The V1 isinstance ladder in
the orchestrator is gone: Research uses `context.memory_results`, Executor
uses `context.working_context`, Memory handles `COMPLETE_SUBTASK` via
`context.goal_service` and writes through `context.memory_service` — each
agent owns its own dispatch. `Agent.run` (base) wraps the legacy sync `call`
in `asyncio.to_thread`, so custom agents inherit protocol compliance for free.

### Services (`services`)

Orchestration no longer touches storage directly. `MemoryService` adds scope
metadata + emits `memory.written`; `SessionService` wraps the turn log;
`GoalService` wraps the goal store. Storage implementations are unchanged
(plus `PRAGMA journal_mode=WAL` on the SQLite stores, matching the
multi-session read/write pattern).

### Memory scoping (`memory.scoping`)

Every write through `MemoryService` carries: `user_id`, `visibility`
(`private`/`shared`/`global`), `session_id`, `origin`, `trust_level`
(`high`/`standard`/`low`). Explicit caller metadata is never clobbered.
**No data migration**: items without `user_id` are legacy single-user items
and will be treated as owner-owned when filtered retrieval arrives. The
filter hook already exists (`where=` on `ChromaMemoryStore.query` →
`MemoryRetriever.search` → `MemoryService.search`) and defaults to off.

### ModelGateway (`modelgw`)

`get_model_gateway().generate(model=…, system=…, prompt=…)` with a provider
registry; `OllamaProvider` is the default and replicates the V1 request
exactly (endpoint, payload, 120 s timeout). Providers raise
`ModelProviderError`; `Agent.call` preserves V1 semantics (log + return `""`).
A future hosted provider is a registration plus `JARVIS_LLM_PROVIDER` —
no architecture change, no cloud dependency today.

---

## 4. Compatibility guarantees

Verified by the test suite (76 tests, all green) and an offline end-to-end
smoke run:

- **CLI** — `python main.py cli` unchanged (`handle()` same shape).
- **API** — all `/api/*` routes and schemas unchanged; `/health` unchanged.
- **Docker** — compose files and entrypoints untouched.
- **Memory / retrieval** — scoring pipeline byte-for-byte identical;
  `where` is opt-in.
- **Planner / critic / reflection / goals** — same prompts, same parsing,
  same semantics.
- **Old import paths** — `orchestrator.task/planner/router/context_optimizer`
  resolve via shims.
- **Offline degradation** — LLM failures still yield `""` responses, never
  exceptions.
- **Single-user operation** — no credentials needed anywhere; everything
  resolves to the owner principal.

Behavioral deltas (all intentional, all additive):
1. Distinct sessions no longer serialize each other (the V1 global lock is gone).
2. New memory writes carry scope metadata (existing data untouched).
3. Lifecycle events are published on the in-process bus.
4. SQLite stores run in WAL mode (a persistent, reversible pragma).

## 5. Migration notes

- **No data migration required.** Chroma metadata is additive; SQLite schema
  unchanged; WAL applies automatically on first open (creates `-wal`/`-shm`
  files next to the DBs).
- **Rollback**: revert the code; data remains compatible in both directions
  (`PRAGMA journal_mode=DELETE` would undo WAL if ever needed).
- **For client developers (Jarvis/Chimera/mobile)**: target `/api/*` as
  today; adopt `protocols.Envelope` for any new streaming/sync surface;
  request an API key entry (`JARVIS_API_KEYS`) per client so per-device
  identity is already in place when enforcement lands.
- **For agent developers**: implement `async run(task, context) -> AgentResult`;
  use `context.memory_service` / `context.goal_service`; never import storage
  directly.

## 6. Remaining Brain V2 phases (unchanged from the design)

| Phase | Theme | Now unblocked by |
|---|---|---|
| 3 (rest) | DAG plans, approval flow, WS streaming, manifests | AgentProtocol, EventBus, Envelope |
| 4 | REST v2 + MCP surface, Chimera integration | Envelope, services, identity |
| 5 | Sync journal + mobile nodes | scoped writes, services as single write path |
| 6 | Cloud-optional (replica, hosted LLM), enforcement, lifecycle jobs | ModelGateway, IdentityService, scoping |
