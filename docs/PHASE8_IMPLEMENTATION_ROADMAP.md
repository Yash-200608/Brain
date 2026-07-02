# PHASE 8 — IMPLEMENTATION ROADMAP

> A practical, ship-first roadmap grounded in the Phase 1–7 findings.
> Date: 2026-06-14 · Prioritized by **impact / effort**. Theoretical work deferred.
> Scales: **Complexity** S (≤2 d) · M (3–10 d) · L (2–4 wk). **Impact** Critical/High/Med/Low. **Risk** Low/Med/High.
> Every task cites the finding/file it comes from — no hypothetical architecture.

## How to read this

The fastest value is **Phase A (stabilization)** — small, low-risk fixes to things
that are already broken or unsafe. The highest *structural* value is the **spine**
(`C1` MQTT bridge → `C2` registry → `C3` skill-as-task) which is what makes the
first real end-to-end Chimera flow possible. Everything else sequences off those.

---

## PHASE A — Stabilization (correct, safe, honest)

| ID | Task | Description | Deps | Cx | Impact | Risk |
|---|---|---|---|---|---|---|
| **A1** | Fail-closed secrets/network | Reject empty `JARVIS_HMAC_KEY`/`RELAY_TOKEN`/`BRIDGE_TOKEN` (today default `""`, `config.py:130`); bind broker + bridges to the Tailscale IP not `0.0.0.0`; drop Brain CORS `*` (`api/server.py`) | — | S | **High** | Low |
| **A2** | Gate the RCE surface | Put `bridge_server.py` destructive ops (run_command/shutdown/file) behind risk confirmation; neutralize `awesome_chat.parse_device_command`'s "never refuse" prompt (disable that edge-cognition path) | A1 | M | **Critical** | Med |
| **A3** | Honest agent failures | `agents/base.py:38/48` — stop returning `""`-as-OK; surface `AgentStatus.ERROR` | — | S | Med | Low |
| **A4** | Golden tests + CI | Freeze `/api/query` request/response; run existing `JARVIS/core/` safety tests in CI | — | Med | Low |
| **A5** | Fix red tests | `test_jarvis.py` imports nonexistent `RateLimiter`/`is_high_risk_request` — fix or delete | — | S | Low | Low |
| **A6** | Storage quick wins | Add indexes `turns(session_id)`, `goals(status)`; bound `jobs.db` growth | — | S | Med | Low |

**Phase A ships:** an honest, fail-closed, tested system with the worst security
holes (Phase 3 #1/#2) closed. No new architecture.

---

## PHASE B — Architecture Cleanup (remove debt, one source of truth)

| ID | Task | Description | Deps | Cx | Impact | Risk |
|---|---|---|---|---|---|---|
| **B1** | Delete dead zones | Remove `models/{reranker,router}.py`, `memory_module.py`, `logging_utils.py`, dead imports (Phase 3 inventory); decide `tools/` (retire — superseded by skill-as-task) | A4 | S | Med | Low |
| **B2** | One wire protocol | Merge `jarvis_prod/protocol.py` + `jarvis/schema.py` (`State`/`Request`/`catalog`); deprecate `jarvis_core`'s `jarvis/phone/*` topics → standardize `jarvis/node/{id}/{verb}` | — | M | **High** | Low |
| **B3** | Enforce the "only door" | `api/routes/{sessions,goals,memory}.py` go through services; kill the 2nd Chroma in `routes/memory.py` (Phase 2 R6) | — | S | Med | Low |
| **B4** | Consolidate dupes | One logger (`main.py` vs `logs/logger.py`); one voice client (`voice_io` keep, retire `voice_module`) | — | S | Low | Low |

**Phase B ships:** a clean base — one protocol, one memory door, dead code gone —
so later work isn't built on ambiguity.

---

## PHASE C — Brain/Jarvis Separation (the spine)

| ID | Task | Description | Deps | Cx | Impact | Risk |
|---|---|---|---|---|---|---|
| **C1** | MQTT bridge (keystone) | NEW `mqtt/`: EventBus ⇄ MQTT; Brain joins the bus (closes Phase 2 M2/A2) | B2 | L | **Critical** | Med |
| **C2** | Device Registry | NEW `devices/`: discover nodes from retained `presence`/`state`/`skills/catalog` (Phase 5 D2) | C1 | M | **High** | Low |
| **C3** | Skill-as-task dispatch | `pipeline.py:159` — `Task.agent` may resolve to a node skill → MQTT `Command`/`Response` (Phase 6 rec) | C1, C2 | M | **High** | Med |
| **C4** | Demote Jarvis brains | Strip planner/critic/memory from `jarvis_core/brain.py` + `brain_pc.py`; keep transport/sensors/executor as node runtime (Phase 2 R1/R2) | C3 | L | High | Med |
| **C5** | Safe actuation + approvals | Route node actuation through `JARVIS/core/executor.py`; risk-1 `ApprovalRequested` flow (Phase 3 #3) | C3 | M | High | Med |
| **C6** | Memory consolidation | Nodes → cache; enforce `memory/scoping.py` filter; retire rival stores (Phase 2 R3) | C1, C4 | M | Med | Med |

**Phase C ships:** Brain is authoritative and on the bus; a plan step performs a
real, safety-gated device action. This is the first time the system matches its own
vision.

---

## PHASE D — Hardware Integration

| ID | Task | Description | Deps | Cx | Impact | Risk |
|---|---|---|---|---|---|---|
| **D1** | Broker on Tailscale | Mosquitto on PC, bound to tailnet, per-node ACLs, MQTT v5 (Phase 5 D3) | A1 | S | **High** | Low |
| **D2** | Nothing Phone node | Run `phone_executor.py` as a Brain-obeying node (template exists) | C2, D1 | M | High | Low |
| **D3** | OPPO/Vivo pinned nodes | Same runtime, single-role (vision / sensors) | D2 | M | Med | Low |
| **D4** | Arduino node | UNO R4 native MQTT via LAN bridge; `gpio.*`/`sensor.*` skills (Phase 5 D5) | C2, D1 | M | Med | Med |
| **D5** | Display surface | `display.*` skill on a host node → TV (HDMI/cast) / salvaged LCD | C3 | M | Low | Low |

**Phase D ships:** a real multi-node mesh — phone(s) + Arduino + a display — all
commanded by Brain.

---

## PHASE E — Multi-Agent Expansion

| ID | Task | Description | Deps | Cx | Impact | Risk |
|---|---|---|---|---|---|---|
| **E1** | Goal-driven loop | Scheduler advances open `goals/` on schedule/events; absorb `jarvis_prod/scheduler.py` (Phase 6 D) | C3 | M | Med | Med |
| **E2** | Event-triggered turns | Node sensor `event`s → EventBus → start a turn/advance a goal | C1 | M | Med | Low |
| **E3** | Dynamic planner catalog | Planner offered only online skills within `risk_ceiling` from the registry (BRAIN_V2 §5.2) | C2, C3 | M | Med | Low |
| **E4** | *(deferred)* DAG plans | `Task.depends_on` + concurrent ready-tasks — only when a workload needs branching | C3 | L | Low (now) | Med |

**Phase E ships:** proactivity — Brain acts on sensor events and pursues goals, and
new hardware becomes plannable with zero Brain edits.

---

## PHASE F — Distributed Cognition

| ID | Task | Description | Deps | Cx | Impact | Risk |
|---|---|---|---|---|---|---|
| **F1** | WS streaming | `/v2/stream` + token streaming + approval frames (envelope exists) (Phase 2 M5) | C1 | M | Med | Low |
| **F2** | MCP server | Expose `brain_query`/`memory_*`/`goals` as MCP tools (Phase 2 M6) | B3 | M | Med | Low |
| **F3** | Identity enforcement | Turn on Brain auth + per-node keys + end-to-end scoping (Phase 2 I1/I2) | C2, C6 | M | **High** | Med |
| **F4** | *(deferred)* Sync + mobile cache | Journal + delta sync + `brainlink` offline (Phase 2 M7) | C6 | L | Med | Med |
| **F5** | *(deferred)* Cloud replica / hosted LLM | Journal subscriber replica; `provider=anthropic` in ModelGateway (Phase 2 M10) | F4 | L | Low | Med |

**Phase F ships:** streaming UX, ecosystem interop (MCP), enforced security, and
(later) offline/cloud resilience.

---

## DELIVERABLE 1 — 30-Day Plan

**Theme: harden + clean + light the broker.** All low-risk, high-leverage.

| Wk | Tasks | Outcome |
|---|---|---|
| 1 | **A1, A4** | fail-closed config; CI golden tests green |
| 2 | **A2, A3, A5** | RCE surface gated; honest failures; red tests fixed |
| 3 | **B1, B3, A6** | dead code gone; service "only door"; DB indexed |
| 4 | **B2, D1** | one merged wire protocol; **Mosquitto on Tailscale up** |

*30-day exit:* the existing system is safe, honest, deduped, and the broker is
running — the launchpad for the spine. **No regressions to `/api/*` or CLI.**

---

## DELIVERABLE 2 — 90-Day Plan

**Theme: build the spine → first end-to-end Chimera flow.** (Includes the 30-day work.)

| Month | Tasks | Outcome |
|---|---|---|
| 1 | Phase A + B1–B3 + D1 | hardened, clean, broker up (above) |
| 2 | **C1, C2** | Brain on the bus; Device Registry discovers nodes |
| 3 | **C3, C5, D2, B4** | skill-as-task + safe actuation; **Nothing Phone node executes a Brain-planned action end-to-end** |

*90-day exit:* **the keystone demo** — speak/type a request → Brain plans →
dispatches a skill over MQTT → phone node executes it safely → result returns.
For the first time the implementation matches the vision.

---

## DELIVERABLE 3 — 6-Month Plan

**Theme: real mesh + proactivity + security.** (Includes 90-day work.)

| Month | Tasks | Outcome |
|---|---|---|
| 4 | **C4, C6** | Jarvis brains demoted to nodes; one authoritative memory |
| 5 | **D3, D4, D5, E2** | OPPO/Vivo/Arduino/display nodes; event-triggered turns |
| 6 | **E1, E3, F1, F3** | goal-driven proactivity; dynamic catalog; WS streaming; enforced identity |

*6-month exit:* a secure, multi-node Chimera mesh where Brain is the single
authority, nodes are thin and safety-gated, sensor events drive proactive goals,
and clients stream responses. Deferred (post-6mo, low ratio): **E4 DAG, F2 MCP
(opportunistic), F4 sync, F5 cloud.**

---

## DELIVERABLE 4 — Priority Matrix (impact / effort)

```
        IMPACT
          ▲
  High    │  C2 · D1 ·        │  A2 · C1 · C3 ·
  ────────│  A1 · B2 · B3     │  C4 · C5 · F3
  (ratio) │  D2 · A4          │  C6 · D4
          │                   │
          │  ───── QUICK WINS ┼ BIG BETS ─────
          │  (do first)       │ (plan & staff)
          │                   │
  Low     │  A3·A5·A6·B1·B4·  │  E4(DAG) · F4(sync)
          │  D5 · E2 · E3·F1  │  F5(cloud)
          │  ── FILL-INS ──   ┼ ── DEFER ──
          └───────────────────┴──────────────────►
             Low effort           High effort   EFFORT
```

- **Quick wins (do now):** A1, A4, B2, B3, C2, D1, D2 — high impact, low/med effort.
- **Big bets (staff carefully):** C1 (keystone), C3, C4, C5, F3.
- **Fill-ins (background):** A3, A5, A6, B1, B4, D5, E2, E3, F1.
- **Defer (low ratio):** E4 DAG, F4 sync, F5 cloud, F2 MCP (opportunistic).

---

## DELIVERABLE 5 — Critical Path Analysis

The path to the **90-day keystone demo** (each step blocks the next):

```
A1 (fail-closed) ──► D1 (broker on Tailscale) ──┐
B2 (one protocol) ──────────────────────────────┤
                                                 ▼
                                        C1 (MQTT bridge)  ◄── keystone / longest pole
                                                 │
                                                 ▼
                                        C2 (Device Registry)
                                                 │
                                                 ▼
                                        C3 (skill-as-task) ──► C5 (safe actuation)
                                                 │
                                                 ▼
                                        D2 (phone node) ──► END-TO-END FLOW
```

- **C1 is the single longest pole** and the keystone — nothing in Phases C–F works
  until Brain is on the bus. Start a spike on it as soon as B2 lands.
- **C4 (demote brains)** is off the critical path to the demo but blocks memory
  consolidation (C6) and clean multi-node ops — schedule right after C3.
- Hardware tasks (D2–D5) each depend only on C2/C3 + D1, so they **parallelize**
  once the spine exists.
- F3 (identity enforcement) depends on C2+C6 — do it before exposing anything
  beyond the tailnet.

---

## DELIVERABLE 6 — Recommended Immediate Next Actions (this week)

Concrete, low-risk, high-leverage — start here:

1. **A1 — fail-closed config** (1–2 d). Reject empty `JARVIS_HMAC_KEY`/tokens; bind
   services to the Tailscale interface; drop CORS `*`. Closes the worst Phase 3 hole
   with the least effort.
2. **A4 — golden tests + CI** (1 d). Freeze `/api/query` and wire the existing
   `JARVIS/core/` safety tests so nothing regresses during the refactor.
3. **B2 — choose & merge the wire protocol** (3–4 d). Standardize on
   `jarvis/node/{id}/{verb}`; merge `protocol.py` + `schema.py`. This unblocks C1.
4. **D1 — stand up Mosquitto on Tailscale** (1–2 d) with per-node ACLs. Cheap, and
   required by everything in C/D.
5. **C1 spike — the MQTT bridge** (start now, time-box). Prove EventBus ⇄ MQTT with
   one phone echoing a command. This is the keystone; de-risk it early.

> Do A1/A4 before touching anything else (safety net first). B2 + D1 can run in
> parallel. Begin the C1 spike the moment B2 is stable — it is the critical path.

---

## Grounding index (task → finding)

| Task | Source finding |
|---|---|
| A1, A2 | Phase 3 Security #1/#2; `config.py:130`, `bridge_server.py`, `awesome_chat` |
| A3 | Phase 6 audit; `agents/base.py:38/48` |
| A6, B1, B4 | Phase 3 Dead Code / Duplication / Scalability inventories |
| B2 | Phase 4 A6; Phase 5 D3 (`protocol.py`, `schema.py`) |
| B3 | Phase 2 R6 (`api/routes/*`) |
| C1 | Phase 2 M2/A2; Phase 7 E1 |
| C2 | Phase 5 D2; Phase 7 E2 |
| C3 | Phase 6 recommendation; Phase 7 E3 (`pipeline.py`) |
| C4 | Phase 2 R1/R2; Phase 7 E4 |
| C5 | Phase 3 #3 (`JARVIS/core/`); Phase 7 E5 |
| C6 | Phase 2 R3; Phase 7 E6 (`memory/scoping.py`) |
| D1–D5 | Phase 5 (hardware/registry/topics) |
| E1–E3 | Phase 6 (hybrid model); Phase 7 E7 |
| F1–F5 | Phase 2 M5/M6/M7/M10, I1/I2 |

> Scope reminder: roadmap only. No code was written; all tasks are proposed work
> against existing files, sequenced for delivery.
