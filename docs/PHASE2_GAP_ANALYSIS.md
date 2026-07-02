# PHASE 2 — GAP ANALYSIS

> Current Implementation **vs** Intended Chimera Vision
> Date: 2026-06-14 · Status: ANALYSIS (no changes proposed)
> Sources of truth: **code** (Phase 1 verified module map) over docs. Intended
> vision drawn from `CLAUDE.md`, `docs/BRAIN_V2_DESIGN.md` (target, marked
> PROPOSED), `docs/BRAIN_V2_FOUNDATION.md` (claimed-implemented foundation).

## Method & severity rubric

Every issue below is grounded in a file/behaviour found in Phase 1. The
"intended" side is cited from `CLAUDE.md` (the Chimera ecosystem charter) and the
Brain V2 docs.

| Severity | Meaning |
|---|---|
| **Critical** | Contradicts a *core premise* of the vision, or a live safety/security hole. The architecture cannot be called "Chimera as designed" while this stands. |
| **High** | A whole intended subsystem is missing/misplaced, or a major mismatch that blocks the vision (contained in scope). |
| **Medium** | Partially built — works but not to spec; or a documented future phase not yet started. |
| **Low** | Doc-vs-code drift, dead imports, cosmetic, naming. |

> Note on "future phases": `BRAIN_V2_DESIGN.md` explicitly defers many items to
> Phases 3–6. Those are flagged **Medium** (planned-not-built) unless the vision
> in `CLAUDE.md` treats them as foundational, in which case they rise to **High**.

---

## THE CENTRAL FINDING — Two brains, zero integration

The single most important gap is structural and dominates everything else:

**`CLAUDE.md` intends one distributed intelligence — Brain owns cognition, Jarvis
is a thin client, MQTT/Tailscale is the nervous system, Brain is authoritative.
The code implements two (really three) *independent, non-communicating*
cognitive systems, and the "nervous system" never reaches the Brain.**

```
INTENDED (CLAUDE.md)                       ACTUAL (code)
─────────────────────                      ─────────────────────────────────
User                                       User
  │                                          ├──────────────┐
  ▼                                          ▼              ▼
Jarvis (thin shell, routing only)        Jarvis repo      Brain repo
  │  (client → server)                   ┌───────────┐    ┌──────────────┐
  ▼                                      │ jarvis_core│    │ FastAPI server│
Brain (memory, agents,                   │  class Brain│   │ core/ pipeline│
  orchestration, knowledge,              │  Planner    │   │ agents, memory│
  device registry)  ◄── authoritative    │  Critic     │   │ Chroma, goals │
  │                                      │  Chroma     │   │ EventBus      │
  ▼                                      │  MQTT       │   │ identity(off) │
MQTT over Tailscale (nervous system)     ├───────────┤    └──────────────┘
  │                                      │ jarvis_prod │         ▲
  ├── PC / Phone / Arduino nodes         │  brain_pc   │         │
                                         │  scheduler  │    NOBODY CONNECTS
                                         │  jobs.db    │    (no client calls
                                         │  telegram   │     /api/*; Brain has
                                         │  MQTT       │     no MQTT at all)
                                         └─────┬──────┘
                                               ▼
                                         MQTT/Tailscale  ↔  phone, bridges
                                         (connects Jarvis-PC ↔ phone ONLY;
                                          Brain is off the bus)
```

**Code evidence:**
- No file in `JARVIS/` references Brain's API (`/api/query`, `:8000`,
  `JarvisOrchestrator`) — the only `/api/` hit is Ollama's `/api/embeddings`.
- No file in `Brain/` imports `paho`/`aiomqtt`/`mqtt`; MQTT is not even in
  `Brain/requirements.txt`. Brain cannot join the MQTT bus.
- `JARVIS/jarvis_core/core/brain.py:137` defines `class Brain`; `:198` runs a
  Planner→Critic loop; `jarvis_core/core/memory.py` opens its own ChromaDB under
  `brain/chroma/`; `jarvis_core/core/config.py:136` configures a
  `knowledge_graph`.

Everything in the four reports below is, directly or indirectly, a consequence of
this split.

---

## System scorecard

### Brain (cognition layer)

| System (per `CLAUDE.md`) | State | Notes |
|---|---|---|
| **Memory** | 🟡 Partial | Chroma + hybrid retrieval + reflection write-back work. Scoping unenforced, graph dead, no sync/lifecycle. |
| **Agent** | 🟡 Partial | 5 role agents + uniform protocol. Sequential only (no DAG), tools dead, status/events unused. |
| **Context** | 🟢 Mostly | `ContextOptimizer` + `TurnContext` work per-turn. `intent.complexity` computed but unused. |
| **Planning** | 🟡 Partial | JSON-step planner → Tasks. No DAG, no manifest catalog, risk-floor gap. |
| **Knowledge** | 🔴 Missing | `memory/graph_builder.py` is fully dead code; no runtime knowledge graph. |
| **Device** | 🔴 Missing | No device registry/model anywhere in Brain. Vision assigns it to Brain. |

### Jarvis (interaction layer)

| Layer | State | Notes |
|---|---|---|
| **Interaction** | 🟡 Heavy | Telegram + CLI + voice exist — but as a *full brain*, not a thin shell. |
| **Voice** | 🟡 Duplicated | `voice_io.py` (in-proc) and `voice_module.py` (HTTP) both implement STT/TTS/wake-word; neither talks to Brain. |
| **Client** | 🔴 Missing | Jarvis is **not** a client of Brain. No `/api/*` call exists. |
| **Execution** | 🟡 Fragmented | Three executors; the *safe* one (`root core/`) is unused; live paths skip it. |

---

## DELIVERABLE 1 — Missing Systems Report

*Features implied by the architecture but not implemented.*

| ID | Missing system | Severity | Intended by | Code reality |
|---|---|---|---|---|
| **M1** | Brain↔Jarvis integration (the "client → server" link) | **Critical** | `CLAUDE.md` data flow `User→Jarvis→Brain→Agent→MQTT` | Zero cross-repo references; Jarvis never calls `/api/*`. |
| **M2** | MQTT nervous system *at the Brain* | **Critical** | `CLAUDE.md` "MQTT is the nervous system… PC Node (Brain host / MQTT broker)" | No MQTT lib in Brain (not in `requirements.txt`); MQTT lives only inside Jarvis. |
| **M3** | Device Registry (a named Brain module) | **High** | `CLAUDE.md` architecture list + "system knows what devices exist" | No device registry/model in Brain; device knowledge lives in Jarvis bridges only. |
| **M4** | Knowledge Layer / knowledge graph (Brain) | **High** | `CLAUDE.md` "Knowledge graph"; `BRAIN_V2_DESIGN.md` §4 Graph tier | `memory/graph_builder.py` never imported/populated — dead. (Jarvis keeps a `knowledge_graph.md` instead.) |
| **M5** | Real-time streaming / WebSocket surface | **High** | `BRAIN_V2_DESIGN.md` §3 WS `/v2/stream` | No WS endpoint; EventBus token-streaming + approvals "defined, not wired." |
| **M6** | REST v2 + MCP server | **Medium** | `BRAIN_V2_DESIGN.md` §3.1 (the documented Chimera/mobile attach surface) | Only V1 `/api/*`; no `/v2/*`, no MCP server (in an MCP-native ecosystem). |
| **M7** | Sync journal + mobile node (`sync/`, `brainlink`) | **Medium** | `BRAIN_V2_DESIGN.md` §3.3/§4 | No `sync/` module, no `journal` table, no delta endpoints. |
| **M8** | Memory lifecycle jobs (decay/consolidation/TTL) | **Medium** | `BRAIN_V2_DESIGN.md` §4 | None implemented. |
| **M9** | Approval flow for risk-1 actions | **Medium** | `BRAIN_V2_DESIGN.md` §5.5 | `ApprovalRequested` + `APPROVAL_GRANTED/DENIED` constants exist; no wiring; risk-1 executes silently. |
| **M10** | Cloud-optional / hosted LLM provider | **Low** | `BRAIN_V2_DESIGN.md` §6 | `ModelGateway` has Ollama only; no second provider registered. |

---

## DELIVERABLE 2 — Incomplete Systems Report

*Partially implemented systems.*

| ID | System | Severity | What works | What's missing |
|---|---|---|---|---|
| **I1** | Identity / auth | **High** | `Principal`, `IdentityService.resolve`, `AuthMiddleware` attach | Non-enforcing: never rejects; default = owner w/ ALL_SCOPES; CORS `*`; `MemoryService.search(principal)` ignores principal. Multi-user is scaffolding. |
| **I2** | Memory scoping | **High** | Scope metadata stamped on write (`memory/scoping.py`) | No retrieval filter enforced (`where` defaults off); no migration; no tenant isolation. |
| **I3** | Jarvis safe-execution layer (`root core/`) | **High** | Full idempotency/validation/safety-rewrite/sandbox/undo/risk pipeline, well-tested | **Not wired into any runtime** — only tests call `execute_task`. Live executors (jarvis_core, bridges) bypass it. |
| **I4** | Agent runtime | **Medium** | Uniform `AgentProtocol.run`, 5 roles dispatched by registry | No DAG/`depends_on`; no `AgentManifest` catalog; `AgentStatus.BLOCKED/ERROR` + `metadata`/`events` defined but never set; failed LLM → silent OK empty output. |
| **I5** | Planner risk gating | **Medium** | Dangerous-token detection raises risk floor | `_risk_floor` only raises to **1**, but pipeline blocks at **≥2** → relies on the LLM to self-assign risk 2. |
| **I6** | Tools layer (Brain) | **Medium** | `Tool`/`ToolRegistry` + 4 tools implemented | Entire `tools/` package is dead — imported only within itself; no agent can call a tool; no manifests/native tool-calling. |
| **I7** | Voice layer (Jarvis) | **Medium** | STT (Whisper/Google), TTS (pyttsx3/ElevenLabs), wake word | Two parallel impls (`voice_io.py` vs `voice_module.py`) with duplicated logic; routes to `awesome_chat` over HTTP, not Brain. |
| **I8** | Dashboard / frontend (Brain) | **Medium** | Vanilla-JS dashboard calls `/api/query`, polls goals | `components/` React set is a placeholder README; status dot never updates; no `/health` poll; API base hardcoded `5173→8000`. |
| **I9** | Episodic/session capture | **Low** | Append-only turn log | `logs/store` `INSERT OR IGNORE` keeps only the first turn's `user_input` at session level; no indexes on `turns(session_id)`/`goals(status)`. |
| **I10** | `jarvis/` clean framework | **Low** | Full symmetric Skill/Router/Schema/Skills framework implemented | Entirely dead — nothing constructs `MQTTRouter`. An abandoned parallel design. |

---

## DELIVERABLE 3 — Responsibility Conflict Report

*Jarvis doing Brain work · Brain doing/Jarvis work · duplicate orchestration · duplicate memory.*

| ID | Conflict | Severity | Evidence | Violated principle |
|---|---|---|---|---|
| **R1** | **Jarvis is a brain** | **Critical** | `jarvis_core/core/brain.py:137` `class Brain` runs Planner(llama3:8b)→Critic(mistral:7b) (`:198`), owns ChromaDB (`memory.py`), a knowledge graph (`config.py:136`), and a scheduler. | `CLAUDE.md`: "Jarvis stays lightweight. Routing and interaction only — **no orchestration logic**." |
| **R2** | **A second Jarvis brain** | **Critical** | `hugginggpt/server/jarvis_prod/brain_pc.py` — another "production PC brain": own scheduler, `jobs.db`, failure-counter "Reflector", Telegram gateway; couples to `awesome_chat.parse_device_command`. | Same as R1; plus single-responsibility. |
| **R3** | **Duplicate / split memory** | **High** | ≥3 independent stores: Brain Chroma `jarvis_memory`; jarvis_core Chroma `brain/chroma`; jarvis_prod `jobs.db`; (dead) `memory_module` deque. None shared. | `CLAUDE.md`: "**Brain owns memory.** Agents never access databases directly." |
| **R4** | **Device work stranded in Jarvis** | **High** | All device control (bridges, ADB, relay, MQTT) is in Jarvis; Brain has no device registry though the vision assigns it to Brain. | `CLAUDE.md` architecture (Device Registry is a Brain module). |
| **R5** | **Duplicate orchestration inside Jarvis** | **Medium** | Four non-interconnected orchestration designs: `jarvis_core` (MQTT reflexion), `jarvis_prod/brain_pc` (MQTT prod), `jarvis/` (dead framework), `awesome_chat` (HuggingGPT). Schema drift: `jarvis/schema.py` vs `jarvis_prod/protocol.py`. | Modular / single-responsibility. |
| **R6** | **Brain bypasses its own "only door"** | **Medium** | `api/routes/sessions.py` & `goals.py` hit stores directly (skip services); `api/routes/memory.py` builds its **own** `MemoryAgent`+Chroma separate from the orchestrator's shared store → two Chroma instances inside Brain. | `BRAIN_V2_DESIGN.md` §2: agents touch memory only via `MemoryService`. |

---

## DELIVERABLE 4 — Architectural Mismatch Report

*Where the implementation contradicts the intended design.*

| ID | Mismatch | Severity | Intended | Actual |
|---|---|---|---|---|
| **A1** | **Authority inverted/absent** | **Critical** | "Brain is the authoritative central server; Jarvis, Chimera, mobile nodes are clients." | Brain is a standalone server nobody connects to; the live Jarvis path is self-contained and never defers to Brain. |
| **A2** | **Nervous system doesn't reach the brain** | **High** | "MQTT (over Tailscale) — all nodes communicate through it" to Brain. | MQTT connects Jarvis-PC ↔ phone only; Brain is entirely off the bus. |
| **A3** | **Forbidden coupling present** | **High** | `CLAUDE.md`: "Flag anything that would tightly couple Jarvis and Brain — that coupling should be avoided." | `brain_pc.py` injects `sys.path` to import `awesome_chat.parse_device_command` — prod brain coupled to the HuggingGPT controller; and Jarvis *embeds* a brain instead of calling the Brain service. |
| **A4** | **Inconsistent inference strategy** | **Medium** | Local-first, cloud-optional via one `ModelGateway`. | Brain = Ollama only. Jarvis = Groq `llama-3.3-70b` (via `awesome_chat`, Langfuse-traced) + Claude adapter + ElevenLabs — cloud-coupled, no shared gateway. |
| **A5** | **Risk-tiered approval contradicted in the live path** | **Medium** | Risk 0 exec / 1 approve / 2 block, with a real approval channel. | `bridge_server.py` exposes `run_command`/`shutdown`/file ops over HTTP (bind `0.0.0.0`); `awesome_chat.parse_device_command`'s prompt tells the LLM to **never refuse** and execute destructive actions with "pre-authorization"; the safe executor (`root core/`) is unused. |
| **A6** | **No single wire-protocol source of truth** | **Medium** | One versioned `Envelope` for WS/events/sync/agent msgs. | Three unrelated contracts: Brain `protocols/envelope` (v2, used by no peer), `jarvis_prod/protocol`, `jarvis/schema`. |
| **A7** | **Pervasive doc-vs-code drift** | **Low** | Docs describe behaviour. | e.g. retriever "rerank" never happens; rate-limit "token-bucket" is fixed-window; `phone_bridge` advertises `record_screen` (absent); `test_jarvis` references nonexistent symbols; many dead imports. |

---

## Master severity index

**Critical (5)** — M1 Brain↔Jarvis link · M2 MQTT-at-Brain · R1 Jarvis-is-a-brain · R2 second Jarvis brain · A1 authority inverted

**High (8)** — M3 device registry · M4 knowledge graph · M5 WS streaming · I1 identity enforcement · I2 memory scoping · I3 unused safe-executor · R3 split memory · R4 stranded device work · A2 MQTT off-bus · A3 forbidden coupling
*(10 listed; M3–M5, I1–I3, R3–R4, A2–A3)*

**Medium (12)** — M6 REST v2/MCP · M7 sync/mobile · M8 lifecycle jobs · M9 approval flow · I4 agent DAG · I5 risk floor · I6 dead tools · I7 voice dup · I8 dashboard · R5 duplicate orchestration · R6 service bypass · A4 inference strategy · A5 live-path risk · A6 wire protocol
*(more than 12 — see tables)*

**Low (5)** — M10 cloud LLM · I9 session capture · I10 dead `jarvis/` framework · A7 doc drift

> **Bottom line for Phase 3+:** the headline is not "features are missing" — most
> *cognitive* pieces exist somewhere. The headline is **mislocation and
> duplication**: the cognition the vision assigns to Brain is largely re-built
> inside Jarvis, Brain is not authoritative and not on the bus, and the
> well-built safety layer is bypassed. Closing the gap is primarily an
> *integration & responsibility-reassignment* problem, not a greenfield build.
