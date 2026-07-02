# PHASE 6 — MULTI-AGENT SYSTEM EVALUATION

> Evaluation of the agent system **as implemented today**. No future designs
> assumed in the audit; recommendations assemble existing pieces.
> Date: 2026-06-14 · Status: EVALUATION · **No code changes.**
> Primary evidence: `core/pipeline.py`, `core/task.py`, `agents/*`,
> `jarvis_core/core/brain.py`, `jarvis_prod/brain_pc.py`, `protocol.py`.

## There are three agent systems today

| # | System | Files | One-line nature |
|---|---|---|---|
| **B-1** | Brain pipeline agents | `agents/`, `core/pipeline.py` | Centralized, **sequential**, blackboard, **LLM-only** (no real tools). |
| **B-2** | jarvis_core reflexion agent | `jarvis_core/core/brain.py`, `executor.py` | Single-node **iterative reflexion** (plan→critic→one tool→repeat); real actuation. |
| **B-3** | jarvis_prod command dispatcher | `jarvis_prod/brain_pc.py`, `protocol.py`, `scheduler.py` | **MQTT command/response** to device nodes; cron/reminders; NL parse via `awesome_chat`. |

They do not interoperate (Phase 2). The evaluation below treats B-1 as the
"Brain agent system" (the one the vision makes authoritative) and uses B-2/B-3 as
contrasting evidence.

---

## DELIVERABLE 1 — Agent System Audit (current code only)

### Agent model

| Aspect | Evidence | Finding |
|---|---|---|
| Uniform contract | `agents/protocol.py` `AgentProtocol.run(task, ctx) -> AgentResult`; `agents/base.py:40` | Clean async protocol; good. |
| LLM call path | `base.py:26` `call()` → `get_model_gateway().generate()` | Single gateway (Ollama). |
| **Silent failure** | `base.py:36-38` — on `ModelProviderError` logs and `return ""` | A failed model call is indistinguishable from an empty answer. |
| **Status always OK** | `base.py:48` default `run()` returns `AgentResult(status=OK)` unconditionally | `AgentStatus.ERROR/BLOCKED` are **never set** by any agent. |
| Roles | `PlannerAgent`, `ExecutorAgent`, `ResearchAgent`, `CriticAgent`, `MemoryAgent` | But Planner/Critic are **not** registry agents — called via bespoke `plan()`/`review()`. |
| Dead result fields | `AgentResult.metadata`, `.events` never populated | The coordination channels exist but carry nothing. |

### Tool execution

| Aspect | Evidence | Finding |
|---|---|---|
| Brain tool layer | `tools/` package imported only within itself (Phase 3) | **Dead — no agent can call a tool.** |
| What ExecutorAgent "does" | `agents/executor.py` → LLM generation over `working_context` | Produces **text**, executes nothing in the world. |
| Only real operations | `MemoryAgent` (search/write/`COMPLETE_SUBTASK`) | Bespoke, not a general tool mechanism. |
| Real actuation exists only in Jarvis | `jarvis_core/core/executor.py` (PC tools + phone), bridges | **Brain cannot act on the world**; the plan→act gap is unbridged in Brain. |

> **Key audit finding:** the Brain "multi-agent system" is a **multi-prompt
> system** — five LLM personas passing text. The single component that touches
> reality (device execution) lives in a different repo and is not reachable from
> the planner.

### Coordination

| Aspect | Evidence | Finding |
|---|---|---|
| Dispatch | `pipeline.py:151` `for t in tasks:` | **Strictly sequential**, one agent at a time. |
| Inter-agent data | `pipeline.py:187` `working = (working + "\n\n" + out)[:max_chars]` | A growing **blackboard string** is the *only* coordination channel. |
| Agent↔agent messaging | none | No agent sends a message to another. |
| Event use | `pipeline.py:184-185` emits `result.events`; lifecycle events emitted | Observability only; **agents never consume events** and never emit any. |
| Concurrency | none (`await` in a serial loop) | No parallel agents even when independent. |
| Failure isolation | `pipeline.py:191` per-task try/except | One task failing doesn't kill the turn (good). |
| Cross-device coordination | only in B-3 (`brain_pc.py` correlates MQTT responses by `Command.id`) | Real coordination exists — but in Jarvis, over MQTT, not in Brain. |

### Planning

| Aspect | Evidence | Finding |
|---|---|---|
| Plan shape | `planner.py:29` → JSON array of `{agent, instruction, risk}` | Flat **ordered list**, produced **once, upfront**. |
| Planner targets | `planner.py:52` agent ∈ `{research, executor, memory}` | Only 3 targets are plannable. |
| **No DAG** | `core/task.py:23` `Task` has **no `depends_on`** | Cannot express parallel/branching plans. |
| Risk gating | `pipeline.py:152` blocks `risk >= 2`; risk 1 executes silently | No approval flow (Phase 2 M9); floor only raises to 1 (Phase 2 I5). |
| Retry | `pipeline.py:106-120` re-runs the **entire plan** if critic not satisfied | Replans nothing; re-executes all steps; silent give-up after `max_retries`. |
| Contrast: B-2 | `jarvis_core/core/brain.py` — single step per call, "the brain will iterate" | Iterative reflexion vs Brain's upfront batch — two opposite planning philosophies in one ecosystem. |

**Audit verdict:** B-1 is a **centralized, sequential, single-shot-plan, blackboard
orchestrator with no tool execution and no real failure signaling.** It is small
and clean, but it is an *orchestration skeleton*, not yet a multi-agent system.

---

## DELIVERABLE 2 — Architecture Comparison

Scored against three axes. ✅ strong fit · 🟡 partial · 🔴 poor/contradicts.

| Option | What it is | Fit: current code | Fit: hardware | Fit: project goals | Evidence anchor |
|---|---|---|---|---|---|
| **A. Centralized orchestration** | One brain plans + dispatches; agents are passive workers | ✅ this *is* B-1 (`pipeline.py`) and B-3 | 🟡 fine for compute, but a Brain-down = mesh-down SPOF | 🟡 matches "Brain authoritative", 🔴 breaks "each node independent if Brain unreachable" | `pipeline.py:151` |
| **B. Distributed agents** | Autonomous peers, P2P decisions | 🔴 zero P2P in code; huge build | 🔴 impossible on Arduino/constrained nodes | 🔴 contradicts "Brain owns cognition/authority" | (absent) |
| **C. Event-driven agents** | Agents react to bus events; loose coupling | 🟡 `events/EventBus` + MQTT exist, but agents don't consume events | ✅ MQTT/sensors are inherently event-driven | 🟡 great for reactions, 🔴 weak at guaranteeing directed goal completion | `events/bus.py`, `sensors.py` |
| **D. Goal-driven agents** | Agents pursue persisted goals, decompose, persist | 🟡 `goals/` + `COMPLETE_SUBTASK` exist but don't *drive* planning | 🟡 needs nodes to report progress | ✅ matches V5 "autonomous intelligence" north star | `goals/store.py`, `memory_agent.py` |
| **E. Hybrid** | Centralized cognition + event transport + goal proactivity + bounded node autonomy | ✅ assembles B-1 pipeline + EventBus + MQTT + goals (all present) | ✅ each node operates at its capability tier | ✅ matches authority *and* fault-tolerance principles | all of the above |

No single pure option fits: **A** recreates the SPOF and ignores the event/sensor
reality; **B** contradicts the vision and the hardware; **C** alone loses the
directed plan→critic→learn loop that *is* the product; **D** is the right north
star but not an architecture on its own at this maturity.

---

## DELIVERABLE 3 — Recommended Agent Model

**Recommendation: E — Hybrid, defined precisely as:**

> **Centralized cognition (A) at Brain · event-driven transport & coordination (C)
> over EventBus⇄MQTT · goal-driven proactivity (D) from `goals/` · bounded
> node autonomy (a sliver of B) for graceful degradation.**

Concretely, reusing what exists:

1. **Cognition stays centralized in Brain** — keep `core/pipeline.py` +
   `WorkerRegistry` as the single planner/dispatcher. Brain decides; nodes don't.
   *(A; already built.)*
2. **Tasks can target node skills, not just in-Brain agents** — extend dispatch so
   a `Task.agent` may resolve to a device **skill** dispatched as an MQTT
   `Command` (`protocol.py`) and awaited as a `Response`. This bridges the
   plan→act gap and makes B-3's MQTT mechanism the execution arm of B-1.
3. **Event-driven coordination** — bridge `EventBus` ⇄ MQTT (Brain on the bus,
   Phase 4 Step 1). Node `event`/sensor topics become `EventBus` events that can
   trigger a turn or advance a goal. *(C; EventBus + MQTT already exist.)*
4. **Goal-driven proactivity** — a goal loop that, on schedule or on events, asks
   the planner to advance open `goals/` subtasks; fold `jarvis_prod/scheduler.py`
   into Brain goals. *(D; goals modeled, just not wired as a driver.)*
5. **Bounded node autonomy** — capable nodes (phones) keep a minimal local
   fallback (B-2 already degrades via heartbeat/`NEED_ATTENTION.md`) but defer to
   Brain whenever it is reachable. Constrained nodes (Arduino) are pure
   command/event actuators. *(graceful degradation, not full distribution.)*

This is **assembly, not greenfield**: every ingredient (pipeline, registry,
EventBus, goals, MQTT protocol, executors) already exists in the codebase — they
are simply not yet connected across the Brain↔Jarvis boundary.

DAG planning (`Task.depends_on`) is **explicitly deferred** — current code is
sequential and that is adequate until plans actually need parallel branches; add
it only when a real workload requires it.

---

## DELIVERABLE 4 — Migration Path

Ordered; each step reuses existing code and is independently shippable. (Aligns
with the Phase 4 spine: contract → reachability → registry → move responsibilities.)

| Step | Action | Reuses | Exit criterion |
|---|---|---|---|
| 1 | **Make agent failures real** — honor `AgentStatus.ERROR`; stop returning `""`-as-OK | `agents/base.py`, `protocol.py` | a failed LLM call surfaces as `ERROR`, not empty success |
| 2 | **Put Brain on the bus** — `EventBus`⇄MQTT bridge | `events/`, `transport.py` | Brain can publish `cmd` / consume node `event`/`response` |
| 3 | **Skill-as-task dispatch** — `Task.agent` can resolve to a node skill (MQTT `Command`) | `pipeline.py:159` dispatch, `protocol.py` | a plan step executes a real device action and returns its `Response` |
| 4 | **Event-triggered turns** — node events/sensors enter `EventBus` and can start a turn | `sensors.py`, `events/bus.py` | a `battery_low` event can trigger a Brain turn |
| 5 | **Goal-driven loop** — scheduler advances open goals via the planner | `goals/`, fold in `jarvis_prod/scheduler.py` | Brain proactively progresses a multi-step goal |
| 6 | **Wire risk/approval + safety executor** — risk-1 approval; route actuation through `JARVIS/core/` | `events` (ApprovalRequested), `JARVIS/core/executor.py` | a risk-1 device action waits for approval; destructive ops gated |
| 7 | *(optional, later)* **DAG** — add `Task.depends_on`, concurrent ready-tasks | `core/task.py`, `pipeline.py` | a 2-branch plan runs concurrently |

---

## DELIVERABLE 5 — Risks and Tradeoffs

| Risk / tradeoff | Severity | Detail | Mitigation |
|---|---|---|---|
| **Centralizing re-asserts the Brain SPOF** | High | Hybrid keeps cognition in one Brain (`pipeline.py`); Brain-down stalls planning | Bounded node autonomy (Step in D3.5) + future replica (`BRAIN_V2_DESIGN` §6) |
| **Skill-as-task widens the RCE surface** | High | Step 3 lets plans trigger real device actions | Land *with* Step 6 (risk gating + safety executor + fail-closed auth, Phase 3) |
| **Event-driven loses traceability** | Medium | Choreography is harder to debug than a serial loop | Correlation ids (`Command.id` already), lifecycle events as a trace, future journal |
| **Goal-driven proactivity → runaway actions** | Medium | Autonomous goal pursuit can act unprompted | Risk tiers + approval flow + per-node `risk_ceiling` (Phase 5 registry) |
| **Eventual consistency across nodes** | Medium | MQTT QoS-1 = at-least-once (duplicates) | Idempotency at the actuator (`JARVIS/core/idempotency.py`) |
| **Hybrid has more moving parts** | Medium | More than pure-centralized | Mitigated by *reusing* existing pieces, one wire protocol, no new frameworks |
| **Sequential-only ceiling** | Low (now) | No concurrency/branching (`task.py` no `depends_on`) | Acceptable today; DAG is Step 7 only if needed |
| **Two planning philosophies persist** | Low | Brain batch-plan vs jarvis_core iterate-plan | Resolve by demoting B-2 to a node (Phase 4 Step 3); Brain's planner becomes the one planner |

### Tradeoff summary

Hybrid trades **maximum availability** (pure-distributed) for **coherent
authority + reuse of what exists**, and trades **maximum simplicity**
(pure-centralized) for **fault-tolerance and event/goal reactivity**. Given the
code (a centralized skeleton that works), the hardware (a few capable nodes + one
constrained MCU), and the goals (authoritative Brain *and* nodes that survive
Brain outages), Hybrid is the only option that honors all three without a rewrite.

> Scope reminder: evaluation only — no agent code, dispatch logic, or protocol
> was modified.
