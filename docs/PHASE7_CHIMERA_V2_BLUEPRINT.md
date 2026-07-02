# PHASE 7 — CHIMERA V2 BLUEPRINT

> The target architecture, **evolved from the existing codebase**. Not a rewrite.
> Date: 2026-06-14 · Status: BLUEPRINT · Synthesizes Phases 1–6.
> Rule of this document: every component names a real existing file and an action —
> **KEEP · MODIFY · WIRE · NEW · RETIRE** — so "maximize reuse" is verifiable.

## Design tenets

1. **One conclusion drove every phase:** the missing piece is not features, it is
   the **integration spine** — *Brain on the bus + one wire protocol + a device
   registry + skill-as-task dispatch*. CHIMERA V2 = building that spine and hanging
   the existing code on it.
2. **Brain decides; nodes sense/present/act** (Phase 4). The PC is the hub *and* a
   node, never a second brain.
3. **Hybrid agent model** (Phase 6): centralized cognition + event-driven transport
   + goal-driven proactivity + bounded node autonomy.
4. **Reuse > rewrite.** Most of the system already exists; it is mislocated and
   disconnected, not absent. The ledger at the end proves the reuse ratio.

---

## DELIVERABLE 1 — CHIMERA V2 Architecture

### 1.1 Runtime Architecture

Three planes (evolved from `BRAIN_V2_DESIGN.md`), now actually connected to nodes.

```
┌──────────────────────────  CLIENTS (Jarvis = thin)  ──────────────────────────┐
│  Voice client   Telegram   CLI   Web/Ops dashboard   (mobile)                  │
└───────────────┬───────────────────────────────────────────────────────────────┘
        north–south: REST /api/* (V1) · WS /v2/stream · MCP   (Envelope)
┌───────────────▼───────────────────────────────────────────────────────────────┐
│  BRAIN — HUB (single authoritative process, asyncio)                            │
│  ┌──────────── protocol plane ────────────┐                                    │
│  │ auth→Principal · session routing · Envelope · Device Registry              │ │
│  ├──────────── cognitive plane ───────────┤   EventBus (in-proc pub/sub)       │
│  │ intent → context → plan → agents → critic → reflect → goals loop           │ │
│  ├──────────── service plane ─────────────┤                                    │
│  │ MemoryService · GoalService · SessionService · IdentityService · ModelGW   │ │
│  └─────────────────────────────────────────┘                                   │
│           ▲  EventBus ⇄ MQTT bridge (NEW)  ▼                                    │
└───────────│───────────────────────────────│───────────────────────────────────┘
            │   east–west: MQTT v5 / Tailscale (jarvis/node/{id}/{verb})         │
   ┌────────┴────────┬───────────────┬──────────────┬─────────────┐
   ▼                 ▼               ▼              ▼             ▼
 PC node         Phone node     Phone node     Constrained    Display
 (actuator)      (Nothing)      (OPPO/Vivo)    node (Arduino) surface
 pc.* skills     phone.* voice  vision/sensor  gpio.*/sensor.* display.* (TV/LCD)
 safety exec     safety exec    safety exec    via bridge      via host node
```

### 1.2 Memory Architecture

**Single source of truth at Brain** (collapses the 5 stores found in Phase 3).

| Tier | Store | Source (existing) | Action |
|---|---|---|---|
| Working | RAM in `SessionActor` | `core/session.py` | KEEP |
| Episodic | SQLite `turns` | `logs/store.py` | KEEP |
| Semantic | Chroma `jarvis_memory` | `memory/store.py` | KEEP (the one authoritative vector store) |
| Procedural | Chroma `kind=insight` | `reflection/` write-back | KEEP |
| Graph/Knowledge | SQLite triples | `memory/graph_builder.py` (dead) | **WIRE** (revive) + absorb Jarvis `knowledge_graph.md` |

- All writes go through `MemoryService` (`services/memory_service.py`) — the **one
  door**; fix the route-layer bypasses (Phase 2 R6). **MODIFY** `api/routes/{memory,sessions,goals}.py`.
- **Enforce scoping** (`memory/scoping.py` exists, filter off) → turn the `where`
  pre-filter on for multi-node/multi-user. **WIRE.**
- **Nodes hold cache only** — node-local Chroma (`jarvis_core/core/memory.py`)
  becomes a read cache + offline write-queue, not a rival store. **MODIFY → cache.**
- Sync journal (append-only) is a later add (`BRAIN_V2_DESIGN` §4) — **deferred**.

### 1.3 Agent Architecture

The **Hybrid** model from Phase 6, made of existing parts:

- **Cognition centralized**: `core/pipeline.py` + `agents/` + `WorkerRegistry`
  remain the one planner/dispatcher. **KEEP.**
- **Skill-as-task dispatch (NEW behavior, existing mechanism)**: a `Task.agent`
  may resolve to *either* an in-Brain cognitive agent (`research`/`memory`) *or* a
  **device skill** dispatched as an MQTT `Command` and awaited as a `Response`.
  **MODIFY** `pipeline.py:159` dispatch; reuse `jarvis_prod/protocol.py` Command/Response.
- **Real failure signaling**: stop returning `""`-as-OK; honor `AgentStatus.ERROR`.
  **MODIFY** `agents/base.py`.
- **Event-driven triggers**: node `event`/sensor topics enter `EventBus` → can
  start a turn or advance a goal. **WIRE** (`events/` + sensors).
- **Goal-driven loop**: `goals/` advanced by a scheduler on schedule/events;
  absorbs `jarvis_prod/scheduler.py`. **NEW driver over existing `goals/`.**
- **Bounded node autonomy**: capable nodes keep a minimal local fallback when Brain
  is unreachable (jarvis_core already degrades via heartbeat/`NEED_ATTENTION.md`).
- **DAG (`Task.depends_on`)**: **deferred** until a workload needs branching.

### 1.4 Device Architecture

- **Device Registry (NEW Brain module `devices/`)** — SQLite + live MQTT view;
  auto-discovers nodes from **retained** `presence`/`state`/`skills/catalog`
  topics; feeds the planner ground truth (replaces `brain_pc._known_skills`).
- **HAL = skills** (revive the dead `hugginggpt/server/jarvis/` framework):
  Brain plans a **capability** (`display.show`, `gpio.write`); the registry routes
  to whichever online node provides it. `pc_skills.py`/`phone_skills.py` are the
  ready-made catalogs. **WIRE (revive).**
- **Node safety**: every actuation routed through `JARVIS/core/executor.py`
  (idempotency/validation/sandbox/undo/risk) — built + tested, currently unused.
  **WIRE.**
- **Node classes** (Phase 5): Hub · Smart · Constrained · Display surface · Peripheral.

### 1.5 Communication Architecture

| Direction | Path | Protocol | Source | Action |
|---|---|---|---|---|
| Client ↔ Brain (north–south) | REST `/api/*` (V1) | HTTP | `api/` | KEEP |
| Client ↔ Brain (streaming) | WS `/v2/stream` | Envelope | `protocols/envelope.py` | NEW endpoint, existing envelope |
| Tooling ↔ Brain | MCP | MCP | — | NEW (optional) |
| Brain ↔ nodes (east–west) | MQTT v5 / Tailscale | `jarvis/node/{id}/{verb}` | `jarvis_prod/protocol.py` + `jarvis/schema.py` | KEEP wire; **MERGE** the two schemas; Brain joins via NEW bridge |
| In-process | EventBus | typed events | `events/` | KEEP |

- **One wire protocol**: standardize on `jarvis/node/{id}/{verb}` (Phase 5); merge
  `schema.py`'s `State`/`Request`/`catalog` into `protocol.py`; **RETIRE** the
  `jarvis_core` `jarvis/phone/*` legacy topics. Brain's `Envelope` is the
  north-south/WS shape; MQTT `Command/Response/Event` is the east-west shape.
- **Brain ⇄ MQTT bridge (NEW)** — the single most important new component; it puts
  the authoritative Brain *on the bus* (closes Phase 2 M2/A2).

### 1.6 Deployment Architecture

Three topologies, each a superset; T1 preserves today exactly.

```
T1 — Single PC (default; = today + bridge + broker)
   docker-compose: brain-api · ollama · mosquitto · dashboard(nginx)
   plus: python main.py cli|api   ·   one phone node optional

T2 — LAN hub + node mesh (the real Chimera)
   PC = Brain + Mosquitto (bound to Tailscale IP)
   Nodes: Nothing/OPPO/Vivo phones (Termux node runtime) · Arduino via bridge
   Remote access: Tailscale (no custom relay needed)

T3 — Cloud-optional (independent toggles)
   - cloud replica (journal subscriber, future) · hosted-LLM via ModelGateway
   - relay_server only if Tailscale unacceptable (reuse existing relay_server.py)
```

Process model: one `brain-api` (asyncio, uvicorn 1 worker — EventBus + actors are
in-proc, per `BRAIN_V2_DESIGN`). Reuse existing `docker/`.

### 1.7 Hardware Architecture

| Device | V2 role | Runtime | Action |
|---|---|---|---|
| Desktop PC | Hub: Brain + Mosquitto + Ollama + PC actuator node | brain-api + node runtime | KEEP/EXTEND |
| Nothing Phone 3a Lite | Smart node (voice + phone skills) | Termux `phone_executor.py` | KEEP (template) |
| OPPO | Smart node pinned → vision/voice terminal | same Termux runtime | REPURPOSE |
| Vivo 1901 | Smart node pinned → sensors/kiosk | same Termux runtime | REPURPOSE |
| Arduino UNO R4 WiFi | Constrained node (gpio/sensor) | native MQTT via LAN/bridge | NEW firmware + bridge |
| TV (HDMI) | Display surface | driven by host node `display.*` | NEW skill |
| Salvaged LCD/speakers/mic | Smart-display terminal (stretch) | LCD+driver board+small host | FUTURE |

---

## DELIVERABLE 2 — Component Diagrams

### Brain internal (hub)

```
                 ┌─────────────────────── api/ ───────────────────────┐
                 │ /api/* (KEEP) · WS /v2/stream (NEW) · MCP (NEW opt) │
                 └───────────────┬─────────────────────────────────────┘
                                 │ Envelope
        ┌────────────────────────▼────────────────────────┐
        │ protocol plane: auth(identity, ENFORCE) ·        │
        │ session routing · Device Registry (NEW devices/) │
        └───────────────┬───────────────────────┬──────────┘
                        │                        │ subscribe/publish
        ┌───────────────▼────────────┐   ┌───────▼─────────────────────┐
        │ core/pipeline (KEEP+MODIFY)│   │ events/ EventBus (KEEP)      │
        │ router·planner·registry·   │◄──┤  ⇄ MQTT bridge (NEW mqtt/)   │
        │ critic·reflector           │   └───────┬─────────────────────┘
        └──────┬──────────────┬──────┘           │ MQTT
               │              │                   ▼  to nodes
   ┌───────────▼──┐   ┌───────▼────────┐   (jarvis/node/{id}/cmd …)
   │ agents/ (KEEP│   │ services/ (KEEP)│
   │ +base MODIFY)│   │ Memory·Goal·Sess│
   └──────────────┘   └───────┬─────────┘
                              │
                    ┌─────────▼──────────┐
                    │ memory/ goals/      │ Chroma + SQLite (KEEP, scoping WIRE)
                    │ reflection/ logs/   │
                    └─────────────────────┘
```

### Node runtime (every Jarvis/phone node)

```
   MQTT (Tailscale)  jarvis/node/{id}/cmd
            │
            ▼
   transport.py (KEEP) ──► signing.py verify (KEEP, fail-closed)
            │
            ▼
   SkillRegistry (REVIVE jarvis/skills.py) ──► resolve skill
            │
            ▼
   JARVIS/core/executor.execute_task (WIRE: idempotency→validate→safety→risk→sandbox)
            │                                   │ risk-1 → approval to Brain
            ▼                                   ▼
   driver: termux-api / pyautogui / gpio / display.*      Response → jarvis/node/{id}/response
   sensors.py (KEEP) ──► Event → jarvis/node/{id}/event
   presence/heartbeat/catalog (retained) ──► Device Registry discovery
   [local fallback brain ONLY if Brain unreachable]
```

---

## DELIVERABLE 3 — Service Boundaries

| Service | Owns | Boundary rule | Existing |
|---|---|---|---|
| **Brain / cognition** | intent, plan, agents, critic, reflect, goals | the only decider; never touches a device directly — emits skill-tasks | `core/`, `agents/`, `goals/`, `reflection/` |
| **MemoryService** | all memory tiers | the *only door* to memory (enforce) | `services/memory_service.py` |
| **Device Registry** | node identity, capabilities, presence | source of truth for "what exists / is online" | NEW `devices/` |
| **Identity** | principals, scopes, per-node keys | resolves + **enforces** auth (fail-closed) | `identity/` (MODIFY) |
| **MQTT bridge** | EventBus ⇄ MQTT translation | the only path Brain↔nodes; no cognition | NEW `mqtt/` |
| **Node runtime** | sense, present, actuate | obeys Brain; decides nothing; safety-gated | `jarvis_core/` (strip brain) |
| **Node actuator** | execute one approved skill safely | idempotent, sandboxed, risk-gated | `JARVIS/core/` (WIRE) |
| **Interaction clients** | voice/telegram/CLI/UI I/O | thin Brain clients; no cognition at edge | voice_io, telegram_gateway |

**Forbidden (anti-patterns from Phase 4):** no planner/critic/memory outside Brain;
no edge LLM device parsing (`awesome_chat.parse_device_command` RETIRED); no direct
store access bypassing services; no node commanding another node (broker ACL).

---

## DELIVERABLE 4 — Data Flow Diagrams

### Flow A — Voice command → device action (canonical)

```
User speaks
  → Voice node: STT (voice_io KEEP) → Request{text} over WS/MQTT
  → Brain: router.classify → memory.search → context build
         → planner.build → Task(agent="phone", skill="phone.ring", risk=1)
  → risk-1 → ApprovalRequested (events) → client grants
  → MQTT bridge: Command → jarvis/node/nothing/cmd
  → Node: verify HMAC → SkillRegistry.resolve → JARVIS/core.execute_task (safe)
         → termux-api ring → Response{ok} → jarvis/node/nothing/response
  → Brain: correlate by Command.id → critic.review → reflector.write (MemoryService)
         → session_service.append_turn → response to client
  → Voice node: TTS speaks confirmation
```

### Flow B — Sensor event → proactive goal

```
Node sensors.py: battery 14% → Event{battery_low} → jarvis/node/oppo/event
  → MQTT bridge → EventBus
  → Goal loop: match/raise goal → planner.build → Command "find charger reminder"
  → (notify via client)   [Brain-initiated, no user prompt]
```

### Flow C — Memory write (single door)

```
Turn output → reflector.reflect → MemoryService.write
  → memory.scoping.apply_scope (user_id, visibility) → ChromaMemoryStore.add
  → MemoryWritten event (EventBus) → [future: journal append for sync]
```

### Flow D — Node discovery (zero-Brain-code onboarding)

```
New node boots → connects (LWT) → publishes RETAINED presence+state+skills/catalog
  → Brain MQTT bridge (subscribed jarvis/node/+/presence, jarvis/skills/catalog/+)
  → Device Registry upserts node + capabilities
  → planner can now target the node's skills (within risk_ceiling)
```

---

## DELIVERABLE 5 — Deployment Model

| Aspect | V2 choice | Reuse |
|---|---|---|
| Brain process | 1× `brain-api` (asyncio, uvicorn 1 worker) + node runtime | `main.py`, `api/server.py` |
| Broker | Mosquitto on PC, bound to **Tailscale IP**, per-node ACLs, fail-closed | NEW config (no broker today) |
| Containers | `docker-compose`: brain-api · ollama · mosquitto · dashboard | extend `docker/` (add mosquitto) |
| Nodes | Termux runtime on phones; Arduino firmware + LAN bridge | `phone_executor.py`, transport |
| Network | MQTT + WS over Tailscale; LAN for constrained nodes | existing Tailscale |
| Secrets | env-only, **fail-closed** (reject empty token/HMAC) | MODIFY config loaders |
| Storage | SQLite WAL + single Chroma on hub; nodes cache only | `data/` (KEEP) |
| Backup (later) | `brainctl backup` (journal + SQLite + Chroma tar) | NEW (deferred) |
| Cloud (optional) | replica (journal subscriber), hosted LLM via ModelGateway | `modelgw/` ready |

Topology adoption: **T1 today → T2 once the bridge + registry land → T3 optional.**

---

## DELIVERABLE 6 — Evolution Strategy

Phased, each milestone independently shippable; **`/api/*` never breaks; single-node
UX never regresses.** Maps the README's V1→V5 ladder onto reuse-first steps.

| Milestone | Theme | Key actions (action·file) | Reuse | Exit criterion |
|---|---|---|---|---|
| **E0 — Safety net** | freeze + harden | golden tests on `/api/query`; **fail-closed** tokens/HMAC; collapse obvious dead code (Phase 3) | KEEP | CI red if V1 surface changes; no empty-secret = open |
| **E1 — The spine** | Brain on the bus | NEW `mqtt/` bridge (EventBus⇄MQTT); broker on Tailscale; merge wire protocol | `events/`, `protocol.py` | a node exchanges envelopes with Brain |
| **E2 — Registry + HAL** | discovery | NEW `devices/`; REVIVE `jarvis/` skills as node SkillRegistry | `pc_skills`, `phone_skills`, `jarvis/skills.py` | Brain answers "what nodes/skills exist" |
| **E3 — Skill-as-task** | plan→act | MODIFY `pipeline.py` dispatch to emit MQTT Commands; honor `AgentStatus.ERROR` | `pipeline.py`, `protocol.py` | a plan step performs a real device action |
| **E4 — Demote Jarvis brains** | one brain | STRIP cognition from `jarvis_core/brain.py` & `brain_pc.py`; keep executor/transport/sensors as node runtime | `jarvis_core/` | no Planner/Critic/Chroma outside Brain |
| **E5 — Safe actuation + approvals** | risk tiers | WIRE `JARVIS/core/executor`; risk-1 approval flow (ApprovalRequested) | `JARVIS/core/`, `events/` | destructive ops gated; risk-1 waits for grant |
| **E6 — Memory consolidation** | one truth | nodes → cache; enforce scoping filter; retire rival stores | `memory/`, `scoping.py` | one authoritative memory; tenant isolation tested |
| **E7 — Goals + proactivity** | autonomy | NEW goal loop over `goals/`; absorb `scheduler.py` | `goals/` | Brain advances a multi-step goal on an event |
| **E8 — Interaction consolidation** | thin clients | one voice client; telegram/CLI → Brain via WS; RETIRE `awesome_chat` cognition | `voice_io`, `telegram_gateway` | single interaction path, no edge cognition |
| **E9 — Optional surfaces** | reach | WS streaming polish, MCP server, cloud replica, hosted LLM | `protocols/`, `modelgw/` | MCP client mounts Brain; replica serves reads |

Sequencing logic: **E1–E2 build the spine (no behaviour change), E3–E5 move
execution onto it, E6–E8 consolidate state/interaction, E9 extends reach.** Each
later milestone depends on the spine, not its siblings.

---

## Reuse ledger (proof of "minimize rewrites")

| Component | Existing file | Action |
|---|---|---|
| Cognitive loop | `core/pipeline.py` | KEEP + MODIFY (dispatch) |
| Session mgmt | `core/{manager,session,...}.py` | KEEP |
| Agents | `agents/*` | KEEP; MODIFY `base.py` (errors) |
| Memory store/retrieval | `memory/{store,retriever,writer,extractor}.py` | KEEP |
| Scoping | `memory/scoping.py` | WIRE (enforce) |
| Knowledge graph | `memory/graph_builder.py` | WIRE (revive) |
| Services | `services/*` | KEEP; enforce one-door |
| Goals | `goals/*` | KEEP + NEW driver |
| Reflection | `reflection/*` | KEEP |
| Identity | `identity/*` | MODIFY (enforce) |
| Envelope | `protocols/envelope.py` | KEEP (north-south) |
| EventBus | `events/*` | KEEP + NEW bridge |
| ModelGateway | `modelgw/*` | KEEP (+cloud opt) |
| HTTP API | `api/*` | KEEP + NEW WS/MCP |
| Dashboard | `frontend/*` | KEEP (as ops client) |
| MQTT client | `jarvis_core/core/transport.py` | KEEP (re-topic) |
| Sensors | `jarvis_core/core/sensors.py` | KEEP |
| Signing | `jarvis_core/core/signing.py` | KEEP (fail-closed) |
| Node template | `jarvis_core/agent/phone_executor.py` | KEEP |
| Wire protocol | `jarvis_prod/protocol.py` (+`jarvis/schema.py`) | KEEP + MERGE |
| Skill framework / HAL | `hugginggpt/server/jarvis/*` | REVIVE |
| Skill catalogs | `jarvis/pc_skills.py`, `phone_skills.py` | KEEP |
| Safe executor | `JARVIS/core/*` | WIRE |
| Relay (off-LAN) | `hugginggpt/server/relay_server.py` | KEEP (optional) |
| Voice | `voice_io.py` (+ retire `voice_module.py`) | CONSOLIDATE |
| Telegram client | `jarvis_prod/telegram_gateway.py` | KEEP (→ Brain client) |
| **Device Registry** | — | **NEW** `devices/` |
| **MQTT bridge** | — | **NEW** `mqtt/` |
| **Goal loop** | — | **NEW** (over `goals/`) |
| Local-brain cognition | `jarvis_core/brain.py`, `brain_pc.py` | RETIRE (strip) |
| Edge LLM parsing | `awesome_chat.parse_device_command` | RETIRE |
| Dead frameworks/modules | `tools/`, `models/{reranker,router}.py`, `memory_module.py`, `logging_utils.py` | RETIRE |

**Net:** ~3 genuinely new modules (`devices/`, `mqtt/`, goal loop) + a handful of
MODIFY/WIRE edits. Everything else is KEEP or RETIRE-dead. The blueprint is an
**integration and consolidation effort, not a rewrite** — exactly the constraint.

> Scope reminder: blueprint only. No code was written; all actions are proposed
> against existing files for a later implementation phase.
