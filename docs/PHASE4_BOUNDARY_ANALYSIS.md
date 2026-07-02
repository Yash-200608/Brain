# PHASE 4 — BRAIN ⇄ JARVIS BOUNDARY ANALYSIS

> Ideal separation of concerns, grounded in the actual codebase.
> Date: 2026-06-14 · Status: DESIGN ANALYSIS · **No code changes.**
> Builds on Phase 1 (verified map), Phase 2 (gaps), Phase 3 (debt).
> Vision sources: `CLAUDE.md` ("Brain owns memory; Jarvis lightweight, routing &
> interaction only; Brain authoritative; MQTT nervous system"), `docs/BRAIN_V2_DESIGN.md`.

## The organizing principle

One sentence resolves almost every boundary question:

> **Brain owns cognition and the single source of truth. Jarvis owns
> human-facing I/O and node-local actuation. A node — including the PC — never
> *decides*; it *senses, presents, and acts* on Brain's behalf.**

Three of the areas you listed are not "Brain or Jarvis" — they are **seams that
must be cut**:

| Area | Cognitive half → **Brain** | I/O half → **Jarvis** |
|---|---|---|
| **Session Handling** | conversational state, working memory, turn ordering | channel/connection identity, reconnect, "which user/device → which Brain session" |
| **Command Routing** | intent understanding, plan/agent dispatch | modality intake, chat-vs-command gating at the edge (no LLM cognition) |
| **Agents** | agent registry, cognitive agents (plan/research/critic/reflect) | node-side **execution** of an approved task (dumb, sandboxed actuator) |

Today these seams are torn the wrong way: cognition leaks *out* to the edge
(`awesome_chat.parse_device_command` does LLM device parsing; `jarvis_core/core/brain.py`
plans and critiques), and authoritative state is *duplicated* at the edge
(jarvis_core Chroma, jarvis_prod `jobs.db`).

---

## DELIVERABLE 1 — Brain Ownership Map

Brain should own everything that **decides, remembers, or is the source of truth.**

| Brain owns | Ideal home | Already there (files) | Status today |
|---|---|---|---|
| **Memory** (working/episodic/semantic/procedural/graph) | `memory/`, `services/memory_service.py` | `memory/store.py`, `retriever.py`, `writer.py`, `extractor.py`, `scoping.py` | ✅ exists; but **duplicated at edge** (jarvis_core Chroma, jarvis_prod jobs.db) |
| **Knowledge graph** | `memory/graph_builder.py` | exists | 🔴 **dead** (never wired); live graph is Jarvis's `knowledge_graph.md` |
| **Context building** | `core/context.py`, `core/context_optimizer.py` | exists | ✅ Brain-only; jarvis_core re-implements its own |
| **Planning** (decompose → steps/DAG) | `core/planning.py`, `agents/planner.py` | exists | ✅ exists; **also** in `jarvis_core/core/brain.py`, `jarvis_prod/brain_pc.py` |
| **Cognitive agents** (research/critic/reflect/memory) | `agents/` | `base.py`, `critic.py`, `research.py`, `memory_agent.py`, `registry.py`, `workers.py` | ✅ Brain-only |
| **Agent orchestration / dispatch** | `core/pipeline.py`, `agents/registry.py` | exists | ✅ exists; duplicated by jarvis brains |
| **Intent / cognitive routing** | `core/routing.py`, `models/classifier.py` | exists | ✅ exists; edge does its own LLM parsing |
| **Goals & scheduling intent** | `goals/`, `services/goal_service.py` | `goals/store.py`, `models.py` | ✅ exists; **cron/reminders duplicated** in `jarvis_prod/scheduler.py`, `jobs.py` |
| **Reflection / learning** | `reflection/` | `reflector.py`, `scorer.py` | ✅ Brain-only; jarvis_prod has a rival "Reflector" failure-counter |
| **Device Registry** (nodes, capabilities, presence) | *new module, Brain* | — | 🔴 **missing**; presence/skills tracked ad-hoc in `jarvis_prod/brain_pc.py` (`_known_skills`) |
| **Identity / authority** | `identity/` | `models.py`, `service.py` | 🟡 exists, non-enforcing |
| **Protocol plane** (the contract nodes connect to) | `protocols/`, `events/`, `api/` | `envelope.py`, `events/`, `api/server.py` | 🟡 envelope exists but no peer; no WS/MCP/bus reach |
| **Session cognitive state** | `core/manager.py`, `core/session.py` | exists | ✅ Brain-only (SessionManager/Actor) |

**Net:** Brain *already implements* almost all of its rightful cognition. The work
is not building it — it is **reclaiming** the copies that leaked to Jarvis and
**exposing** a surface nodes can reach (device registry + WS/MQTT/MCP).

---

## DELIVERABLE 2 — Jarvis Ownership Map

Jarvis (and every node) should own everything that **touches a human or touches hardware** — and nothing that decides.

| Jarvis owns | Ideal home | Today (files) | Status |
|---|---|---|---|
| **Voice I/O** (STT, TTS, wake word) | one consolidated voice client | `hugginggpt/server/voice_io.py`, `voice_module.py` | 🟡 exists but **duplicated**; routes to `awesome_chat`, not Brain |
| **User interaction shell** (voice/telegram/CLI/mobile) | thin per-modality clients | `jarvis_prod/telegram_gateway.py`, `awesome_chat.py` (cli/server) | 🟡 exists, but fused with cognition |
| **End-user UI** | Jarvis client(s) | Brain `frontend/dashboard/` is the only UI today | 🟡 Brain dashboard is fine as an **ops/debug client**, but the *user* UI belongs to Jarvis |
| **Connection/channel session** (user/device → Brain session, reconnect) | gateway layer | partial: `brain_pc.py` presence/state | 🟡 ad-hoc |
| **Command intake routing** (modality + chat-vs-command gate) | edge router, **no LLM** | `device_integration.py`, dead `jarvis/router.py` | 🔴 today an LLM parses commands at the edge (`awesome_chat.parse_device_command`) |
| **Node device execution** (the actuator) | node-side safe executor | `jarvis_core/core/executor.py`, `agent/phone_executor.py`, `bridge_server.py`, `phone_bridge.py`, `phone_agent.py` | 🟡 works, but **bypasses** the safety layer |
| **Local safety enforcement** at the actuator | wire in the existing one | `JARVIS/core/` (idempotency/validation/sandbox/undo/risk) | 🔴 **built + tested, unused** |
| **Sensors / presence reporting** | node → Brain | `jarvis_core/core/sensors.py`, heartbeats | ✅ exists (but reports to local brain, not Brain) |
| **Transport to Brain** | MQTT/WS client | `jarvis_core/core/transport.py`, `jarvis_prod/protocol.py` | ✅ MQTT exists — but points node↔node, not node↔Brain |

**Net:** Jarvis's rightful pieces (voice, transport, sensors, executors) mostly
exist and are decent. The problem is they are wrapped around a *local brain*
instead of pointed at *the* Brain — and the best safety code is switched off.

---

## DELIVERABLE 3 — Responsibility Matrix

`Verdict` legend: **KEEP** (right place) · **MOVE** (wrong layer) · **SPLIT** (cut the seam) · **CONSOLIDATE** (dedupe) · **BUILD** (missing) · **WIRE** (exists, connect it).

| Capability | Current owner (files) | Ideal owner | Verdict |
|---|---|---|---|
| Semantic/episodic memory | Brain `memory/` **+** jarvis_core `core/memory.py` **+** Brain `api/routes/memory.py` (2nd Chroma) | **Brain** | CONSOLIDATE → Brain; nodes get cache only |
| Knowledge graph | Brain `graph_builder.py` (dead) **+** jarvis_core `knowledge_graph.md` (live) | **Brain** | MOVE edge graph → Brain; WIRE Brain's |
| Context building | Brain `core/context*` **+** jarvis_core `brain.py` | **Brain** | CONSOLIDATE → Brain |
| Planning | Brain `core/planning.py` **+** jarvis_core `brain.py` **+** jarvis_prod `brain_pc.py` | **Brain** | CONSOLIDATE → Brain |
| Critic / verification | Brain `agents/critic.py` **+** jarvis_core `brain.py` | **Brain** | CONSOLIDATE → Brain |
| Reflection / learning | Brain `reflection/` **+** jarvis_prod Reflector | **Brain** | CONSOLIDATE → Brain |
| Goals / cron / reminders | Brain `goals/` **+** jarvis_prod `scheduler.py`/`jobs.py` | **Brain** (intent) + node (exec) | CONSOLIDATE intent → Brain |
| Intent classification | Brain `core/routing.py` **+** edge `awesome_chat.parse_device_command` | **Brain** | MOVE cognition off edge |
| Device registry / presence | *none* + ad-hoc `brain_pc._known_skills` | **Brain** | BUILD in Brain |
| Agent execution (device actuation) | jarvis_core `executor.py`, bridges, `phone_agent.py` | **Jarvis/node** | KEEP (as dumb actuator) |
| Execution safety | `JARVIS/core/` (unused) | **Jarvis/node** | WIRE it in |
| Voice I/O | `voice_io.py` + `voice_module.py` | **Jarvis** | CONSOLIDATE to one |
| User UI | Brain `frontend/` | **Jarvis** (Brain dashboard = ops client) | SPLIT/relabel |
| Conversational session state | Brain `core/manager.py`/`session.py` | **Brain** | KEEP |
| Connection/channel session | `brain_pc.py` partial | **Jarvis** | SPLIT + BUILD |
| Command intake routing | `device_integration.py`, dead `jarvis/router.py` | **Jarvis** (no LLM) | KEEP intake, MOVE cognition out |
| Transport (MQTT/WS) | jarvis_core `transport.py`, jarvis_prod `protocol.py` | **shared** (node↔Brain) | RE-POINT to Brain |
| Wire protocol | Brain `envelope.py` + `jarvis_prod/protocol.py` + `jarvis/schema.py` | **Brain defines** | CONSOLIDATE to one |
| Auth / scopes | Brain `identity/` (off) | **Brain** | WIRE/enforce |

---

## DELIVERABLE 4 — Migration Plan (no code now — sequence & exit criteria)

Dependency-ordered. Each step is independently shippable and reuses existing code
wherever possible. **`/api/*` and current single-node behaviour must never break.**

**Step 0 — Freeze the boundary contract.**
Define the node↔Brain protocol on top of Brain's existing `protocols/Envelope`,
folding in the proven message set from `jarvis_prod/protocol.py` (cmd/response/
event/presence/heartbeat). Deliverable: one wire spec. *Exit:* a documented
envelope all nodes and Brain agree on; the other two schemas marked deprecated.

**Step 1 — Make Brain reachable by nodes.**
Add the transport surface Brain lacks: a WS `/v2/stream` and/or an MQTT bridge so
Brain is *on the bus*. Reuse `events/EventBus` as the internal fan-out.
*Exit:* a node can connect to Brain and exchange envelopes; Brain off-bus problem
(Phase 2 A2 / M2) closed.

**Step 2 — Build the Device Registry in Brain.**
New Brain module: nodes register (id, capabilities/skills, presence) and
heartbeat. Source the capability list from today's `jarvis/pc_skills.py` /
`phone_skills.py` catalogs. *Exit:* Brain can answer "what nodes/skills exist"
(closes Phase 2 M3); replaces `brain_pc._known_skills`.

**Step 3 — Demote the Jarvis "brains" to nodes.**
Strip planning/critic/memory from `jarvis_core/core/brain.py` and
`jarvis_prod/brain_pc.py`; keep their **executor, transport, sensors, scheduler-
trigger** as node capabilities that report to and obey Brain. *Exit:* no
Planner/Critic/Chroma instantiated outside Brain (closes Phase 2 R1/R2).

**Step 4 — Consolidate memory to Brain; nodes cache only.**
Point all recall/write at Brain `MemoryService`. Node-local store becomes a
read cache + offline write queue (the `brainlink` idea in `BRAIN_V2_DESIGN.md`
§6). Retire jarvis_core Chroma and the 2nd Chroma in Brain `api/routes/memory.py`.
*Exit:* one authoritative memory (closes Phase 2 R3, Phase 3 dup).

**Step 5 — Wire the safety executor as the node actuator.**
Route every device action through the existing `JARVIS/core/executor.execute_task`
(idempotency/validation/sandbox/undo/risk) instead of raw bridge/awesome_chat
execution. *Exit:* destructive ops gated by the risk tiers (closes Phase 3 #1/#3).

**Step 6 — Consolidate interaction & voice.**
One voice client (merge `voice_io.py` + `voice_module.py`); telegram/CLI/voice all
become thin Brain clients via Step 1's surface. Remove edge LLM parsing
(`awesome_chat.parse_device_command`). *Exit:* a single interaction path; cognition
no longer at the edge.

**Step 7 — Enforce identity + retire dead zones.**
Turn on Brain auth/scoping (per-node keys), fail-closed tokens/HMAC. Delete the
abandoned `jarvis/` framework, Brain `tools/` (or wire it), and dead modules from
the Phase 3 inventory. *Exit:* fail-closed perimeter; dead code removed.

> Ordering rationale: Steps 0–2 build the *spine* (contract + reachability +
> registry) without touching behaviour; Steps 3–5 move responsibilities onto that
> spine; Steps 6–7 clean up. Each later step depends on the spine, not on its
> siblings, so they can ship one at a time.

---

## DELIVERABLE 5 — Anti-Patterns Report

| Anti-pattern | Where (files) | Why it hurts |
|---|---|---|
| **God-node / brain-at-the-edge** | `jarvis_core/core/brain.py`, `jarvis_prod/brain_pc.py` | Two+ full cognitive systems outside the authoritative Brain; violates "Jarvis lightweight". |
| **Multiple sources of truth** | memory ×5 (Brain Chroma, jarvis_core Chroma, jarvis_prod `jobs.db`, dead `memory_module`, Brain route's 2nd Chroma); wire schema ×3 | Divergence, no canonical state, sync impossible. |
| **Cognition at the I/O layer** | `awesome_chat.parse_device_command` (LLM device parsing in the interaction tier) | Decisions made where they can't see memory/goals; also a prompt-injection RCE vector. |
| **Abandoned parallel rewrites** | `hugginggpt/server/jarvis/*`, Brain `tools/*`, `JARVIS/core/*` | Complete frameworks built then bypassed; reader can't tell the live path. |
| **Tested-but-unwired safety** | `JARVIS/core/executor.py` (only tests call it) | The best safety code protects nothing in production. |
| **Fail-open defaults** | `RELAY_TOKEN`/`BRIDGE_TOKEN`/`JARVIS_HMAC_KEY` default `""`; Brain auth non-enforcing, CORS `*` | Security depends on remembering to set env; absent config = wide open. |
| **sys.path coupling** | `brain_pc.py` injects parent dir to import `awesome_chat` | Hard cross-module coupling the vision explicitly says to flag. |
| **Silent failure swallowing** | `agents/base.py` `Agent.call` returns `""` on `ModelProviderError`; critic silent give-up | Errors masquerade as empty success; undebuggable. |
| **Bypassing the "only door"** | Brain `api/routes/sessions.py`/`goals.py` hit stores directly; `routes/memory.py` builds its own agent+store | The service-layer invariant is asserted in docs, broken in code. |
| **Singletons-at-import / hidden globals** | Brain route modules build orchestrators at import; `core/config.EXECUTION_MODE` global; `executor._approved_commands` module dict | Import side-effects, untestable, blocks horizontal scale. |
| **Duplicate-by-fork** | `phone_bridge.py` vs `phone_agent.py` vs `phone_skills.py` vs `phone_executor.py`; `voice_io` vs `voice_module`; signing copied inline | Every fix must be applied N times. |

---

## One-page picture — ideal boundary

```
            ┌──────────────────────────  JARVIS / NODES (thin)  ──────────────────────────┐
            │  Voice client   Telegram   CLI   Mobile U  │  PC node   Phone node   Arduino │
            │  (STT/TTS/wake) (chat)    (chat) (web)     │  executor  executor     sensors │
            │        └──── interaction shell ────┘       │  (safety-gated actuators)       │
            └───────────────┬───────────────────────────┴───────────────┬─────────────────┘
                            │ envelope over WS / MQTT (Brain's contract)  │ task.assign / result
            ┌───────────────▼─────────────────────────────────────────────▼─────────────────┐
            │  BRAIN (authoritative, one process)                                            │
            │  protocol plane: auth → principal · session routing · envelope · device reg.   │
            │  cognition: intent → context → plan(DAG) → agents → critic → reflect           │
            │  state (single source of truth): memory(all tiers) · knowledge graph · goals   │
            │  services: MemoryService · GoalService · SessionService · ModelGateway          │
            └────────────────────────────────────────────────────────────────────────────────┘
```

> Scope reminder: this phase **analyzes and plans the boundary only**. No files
> were modified; the migration steps are sequencing, not implementation.
