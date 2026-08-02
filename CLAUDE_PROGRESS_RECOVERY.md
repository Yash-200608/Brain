# Claude Progress Recovery Report

> **Generated:** 2026-08-02  
> **Scope:** Chimera ecosystem — `Brain` + `JARVIS` repositories  
> **Method:** Read-only archaeology (source, docs, git history, markers, diffs)  
> **Constraint:** No code was modified during this investigation except creation of this report.  
> **Authorship note:** Git commits are authored by **Yash** (`yashkadyan2008@gmail.com`). There is no git identity named “Claude”; Claude’s work is reconstructed from docs (PHASE/PRIORITY/ADR), `.claude/skills/`, commit messages, and code state.

---

# Executive Summary

Claude (and/or Claude-assisted sessions) left behind a **deliberate, well-documented multi-priority program** to turn a fragmented “four islands” assistant into a **Brain-owns-cognition / JARVIS-owns-embodiment** system over signed MQTT.

| Layer | Verdict |
|-------|---------|
| **Audit & architecture (June–July 2026)** | **Complete** — PHASE 2–8, ADRs 011–014, ecosystem architecture |
| **Priority #1 (security)** | **Closed** |
| **Priority #2 (ADRs / readiness)** | **Closed** |
| **Priority #3 (execution spine)** | **Closed** — live ping E2E proven |
| **Priority #4 (cognitive dispatch + keystone demo)** | **~75% of milestones shipped in code; demo/trial not started** |
| **Overall Chimera vision (voice, multi-hardware, KG, legacy retirement)** | **~45–55%** — spine + skills exist; daily use still on legacy stack |

**Where work stopped:** Brain is **4 commits ahead of origin** on Priority #4 M1/M2/M4/M7. JARVIS is **7 commits ahead** with M2/M3/M5/M6/M8/M9 (software half). **Uncommitted Brain WIP (77 lines)** starts Priority #4 **M10** (`POST /{node}/invoke` + `approver_keys`). Dashboard still only has **Ping** — no invoke/approval UI. **M11 Keystone Demo** and **M12 ADR-014 retirements** have not started. `awesome_chat.py` remains daily production.

---

# Current Project State

## Repositories

| Repo | Path | Role | Branch state |
|------|------|------|--------------|
| **Brain** | `C:\Users\Hp\OneDrive\Desktop\Brain` | Sole cognitive authority (ADR-011) | `main` ahead of `origin/main` by **4**; 4 uncommitted files |
| **JARVIS** | `C:\Users\Hp\OneDrive\Desktop\JARVIS` | Embodiment / nodes / legacy stacks | `main` ahead of `origin/main` by **7**; clean working tree |

## What “Claude was building”

Evidence chain (docs + commits):

1. **June 2026 audits** (`docs/PHASE2`–`PHASE8`) diagnosed two disconnected brains, Brain off MQTT, security debt, dead tools.
2. **July 2026 governance** — `CHIMERA_ECOSYSTEM_ARCHITECTURE.md`, ADR-011–014, Priority #1–#3.
3. **Priority #3** — signed `chimera/<node>/…` spine, device registry, ping E2E (`docs/audits/PRIORITY-3-EXECUTION-SPINE-CLOSURE.md`).
4. **Priority #4** — frozen plan `docs/PRIORITY-4_DEFINITION.md` (2026-07-04): NL → Brain plan → risk/approval → MQTT skills → Keystone Demo → legacy retirement.

## Active vs legacy runtime

| Runtime | Location | Status |
|---------|----------|--------|
| Brain API + cognitive pipeline | `Brain/main.py`, `api/`, `core/pipeline.py` | Runnable; MQTT off by default (`mqtt_enabled=false`) |
| Chimera node (active path) | `JARVIS/run_chimera_node.py` + `jarvis_node_sdk/` | Built; M8/M9 software shipped; live Tailscale phone ops not evidenced in-repo |
| Legacy daily assistant | `JARVIS/hugginggpt/server/awesome_chat.py` | **Still daily use** (ADR-014 gate) |
| jarvis_prod | `JARVIS/hugginggpt/server/jarvis_prod/` | Smoke-tested; parallel `jarvis/node/…` MQTT world |
| jarvis_core cognition | `JARVIS/jarvis_core/` | Prototype; never E2E; freeze deferred to P4-M12 |

---

# Completed Work

## A. Documentation & governance (complete)

| Artifact | Path | Evidence |
|----------|------|----------|
| Ecosystem charter | `Brain/CLAUDE.md`, `JARVIS/CLAUDE.md` | Shared Chimera context |
| Canonical architecture | `Brain/docs/CHIMERA_ECOSYSTEM_ARCHITECTURE.md` | ADR-011 by reference |
| Decision log ADR-011–014 | `Brain/docs/DECISION_LOG.md` | Lines 11–174+ |
| PHASE audits 2–8 | `Brain/docs/PHASE2_GAP_ANALYSIS.md` … `PHASE8_IMPLEMENTATION_ROADMAP.md` | Analysis-only; no code |
| V2 design vs foundation | `Brain/docs/BRAIN_V2_DESIGN.md`, `BRAIN_V2_FOUNDATION.md` | Design vs implemented |
| P3 closure | `Brain/docs/audits/PRIORITY-3-EXECUTION-SPINE-CLOSURE.md` | Capstone met |
| P4 frozen plan | `Brain/docs/PRIORITY-4_DEFINITION.md` | M1–M12 table ~L498–511 |
| Claude skills | `Brain/.claude/skills/`, `JARVIS/.claude/skills/` | 10 persona skills each |
| Brain CI | `Brain/.github/workflows/ci.yml` | ruff + mypy + pytest |
| Node provisioning | `JARVIS/docs/ops/NODE_PROVISIONING.md` | P4 M9 ops |

## B. Priority #1–#3 (closed)

| Priority | Closure evidence |
|----------|------------------|
| #1 Security | Commit `4b72501` / JARVIS `4d52383`; fail-closed auth; dashboard auth restored (`f865ac7`) |
| #2 ADRs | Commits `eda4c90`, `7b25460`, `5019880`; audits in `docs/audits/` |
| #3 Spine | Commit `e5d337f` / JARVIS `6dd840f`; 12 milestones; live ping; Brain tests 111→174 |

## C. Priority #4 milestones completed in git

| Milestone | Repo | Commit / evidence | Status |
|-----------|------|-------------------|--------|
| **M1** Scope enforcement | Brain | `bbd74e9`; `api/deps.py`, `test_scope_enforcement.py` | **Done** |
| **M2** Correlation ID | Both | Brain `7a49961`; JARVIS `ffe9eb8` | **Done** |
| **M3** Capability declaration (node) | JARVIS | `93da948`; `jarvis_node_sdk/capabilities.py` | **Done** |
| **M4** Capability registry (Brain) | Brain | `e0091b4`; `mqtt/capabilities.py` | **Done** |
| **M5** Real phone skills | JARVIS | `e6cd2ac`; `jarvis_node_sdk/phone_skills.py` + tests | **Done** (software) |
| **M6** PC skills + safety kernel | JARVIS | `10d4fd0`; `pc_skills.py` through root `core/` | **Done** (software) |
| **M7** Dispatch bridge + NP-7 approval | Brain | `09351c0`; `core/device_intents.py`, `agents/device_agent.py`, `devices/approvals.py`, approval routes | **Done** |
| **M8** Production node entrypoint | JARVIS | `2f545e9`; `run_chimera_node.py` | **Done** (software; 24h live soak not evidenced) |
| **M9** Phone provisioning (software half) | JARVIS | `ae60a1a`; `scripts/termux_install.sh`, `NODE_PROVISIONING.md` | **Partial** — installer+docs; hardware live proof not in-repo |

## D. Brain V2 foundation (largely complete)

| Module | Path | Status |
|--------|------|--------|
| Session manager | `core/manager.py`, `core/session.py` | Complete |
| Cognitive pipeline | `core/pipeline.py` | Complete (+ device turn path) |
| Agents | `agents/*` | Functional multi-prompt system |
| Memory (Chroma hybrid) | `memory/store.py`, `retriever.py`, … | Retrieval works |
| Identity + scopes | `identity/` | Implemented; HTTP fail-closed |
| EventBus | `events/` | Foundation complete |
| Model gateway | `modelgw/` | Ollama only |
| Goals / reflection / logs | `goals/`, `reflection/`, `logs/` | Wired |
| FastAPI surface | `api/` | Query, memory, goals, sessions, devices |
| Ops dashboard | `frontend/dashboard/` | Chat + memory + goals + devices + ping |

---

# Work In Progress

## 1. Priority #4 M10 — Brain API half (UNCOMMITTED)

**Files (working tree, +77 / −1):**

| File | Lines (approx.) | What |
|------|-----------------|------|
| `api/routes/devices.py` | ~166–210 | `POST /{node}/invoke` — risk gate, approval_required, or dispatch |
| `api/schemas.py` | ~49–51 | `InvokeIn` schema |
| `config/config.py` | ~57–62 | `approver_keys` setting |
| `identity/service.py` | ~42–59 | Seed approver principals with `devices.approve` + `devices.read` |

Docstring in uncommitted `invoke_skill` explicitly labels this **“Priority #4 Milestone 10”**.

**Not yet present for M10:**

- Dashboard invoke / approval / audit UI (`frontend/dashboard/app.js` still Ping-only, ~L104–208)
- Documented multi-node concurrent live proof
- Commit of the 4 Brain files

## 2. Priority #4 M9 — ops half

- Software: `scripts/termux_install.sh`, provisioning doc — **present**
- Evidence of Nothing Phone live over Tailscale answering `phone.battery` — **not found in repository**

## 3. Doc drift (living status docs stale)

| Doc | Issue |
|-----|-------|
| `JARVIS/docs/context/CURRENT_STATUS.md` | Last updated 2026-07-04; misses P4 M5–M9 |
| `Brain/docs/BRAIN_V2_FOUNDATION.md` | Still describes non-enforcing auth in places |
| Comments in `identity/service.py`, `api/routes/query.py`, `config/config.py` | Still say “non-enforcing” / “future phase” while HTTP scopes enforce |

## 4. Memory scoping (foundation only)

```40:45:Brain/services/memory_service.py
        """Hybrid-scored retrieval (V1 pipeline, unchanged).

        ``principal`` is accepted now so call sites are already
        identity-aware; scoped filtering switches on in a future phase.
        """
        return self.memory_agent.search(query, top_k=top_k, where=where)
```

---

# Unfinished Features

| Feature | Planned in | Evidence of incompleteness | Status |
|---------|------------|----------------------------|--------|
| Dashboard command console | P4 M10 | No invoke/approval UI in `frontend/dashboard/` | **Incomplete** |
| Keystone Demo + trial | P4 M11 | No trial instrumentation / outcome docs | **Not started** |
| ADR-014 retirements | P4 M12 | `awesome_chat`, `brain_pc`, `bridge_server`, jarvis_core still present | **Not started** |
| Multi-user memory read filtering | V2 / future | `memory_service.py` L42–44 | **Planned** |
| Knowledge graph | V4+ | `memory/graph_builder.py` — never imported | **Unwired** |
| Tool layer | V2 design vs PHASE7 conflict | `tools/` — zero callers | **Orphaned** |
| Reranker / ModelRouter | Retriever docs | `models/reranker.py`, `models/router.py` unused | **Unwired** |
| MQTT `#` wildcards (Brain) | `mqtt/client.py` ~L21–22 | Deferred comment | **Planned** |
| Token streaming / ApprovalRequested events | `events/types.py` | Types defined, never emitted | **Stub types** |
| WebSocket / MCP / sync journal | `BRAIN_V2_DESIGN.md` | Packages/routes absent | **Not built** |
| Voice → Chimera | `JARVIS/docs/specifications/VOICE_SYSTEM.md` | Legacy `voice_module.py` HTTP only | **Not integrated** |
| Arduino / OPPO / Vivo / tablet LCD nodes | `CLAUDE.md` inventory | No node code | **Not started** |
| React component extraction | `frontend/components/README.md` | Aspirational only | **Planned** |
| JARVIS CI | — | No `.github/workflows` | **Missing** |
| `authority_scope` envelope field | Deferred to P5 | `PRIORITY-4_DEFINITION.md` L523–527 | **Deferred** |

---

# Inferred Next Steps

Based **only** on `PRIORITY-4_DEFINITION.md` sequencing and repo state:

1. **Commit / finish Brain M10 API** — land uncommitted `invoke` + `approver_keys`.
2. **Complete M10 UI** — dashboard per-skill invoke, approval queue, audit view (`PRIORITY-4_DEFINITION.md` L509).
3. **Prove multi-node live** — PC + phone concurrent over Tailscale (M9 ops + M10).
4. **M11 Keystone Demo** — execute demo checklist; start outcome-based trial replacing daily legacy commands.
5. **M12** — trial outcome report; execute or defer ADR-014 retirements with evidence; write `PRIORITY-4-CLOSURE.md`.
6. **Priority #5 (deferred list)** — `authority_scope`, dead-code hygiene, MQTT TLS/ACLs, voice, EventBus↔MQTT generalization, etc.

---

# Architecture Overview

## Ecosystem boundary (ADR-011)

```
USER / Dashboard / Voice (future)
        │
        ▼
   BRAIN (cognition)                    JARVIS (embodiment)
   ┌─────────────────────┐              ┌──────────────────────────┐
   │ SessionManager      │              │ run_chimera_node.py      │
   │ CognitivePipeline   │── MQTT ─────▶│ jarvis_node_sdk/         │
   │ DeviceDispatcher    │  chimera/    │  phone_skills / pc_skills│
   │ ApprovalStore       │  <node>/cmd  │  root core/ safety kernel│
   │ DeviceStore         │◀─ response ─│  presence/state/caps     │
   │ Memory / Goals      │              └──────────────────────────┘
   └─────────────────────┘
        ▲
        │ HTTP Bearer + scopes
   frontend/dashboard (ops)
```

## Brain module map

| Package | Responsibility |
|---------|----------------|
| `api/` | FastAPI, auth, rate limit, routes |
| `core/` | Sessions, pipeline, routing, planning, device intents |
| `agents/` | Planner, critic, executor, research, memory, device |
| `devices/` | Registry, dispatcher, approvals, audit, policy |
| `mqtt/` | Client, signed commands, presence/state/capabilities |
| `protocols/` | North-south `Envelope`; east-west `ChimeraEnvelope` |
| `memory/`, `services/` | Storage + service facades |
| `identity/` | Principals, scopes, API/approver keys |
| `orchestrator/` | V1-compatible `JarvisOrchestrator` facade |
| `tools/` | **Dead** tool registry |
| `models/` | Embeddings/classifier used; reranker/router unused |

## Startup sequence (Brain API)

1. `python main.py api` → uvicorn with Windows `SelectorEventLoop` workaround (`main.py`).
2. `api/server.py` lifespan: if `mqtt_enabled` and HMAC key → start `BrainMqttClient`, subscribe presence/state/capabilities.
3. Middleware: CORS → rate limit → fail-closed auth.
4. Routers: query, memory, goals, sessions, devices.
5. Orchestrator wires pipeline + `DeviceDispatcher` + `ApprovalStore` (P4 M7).

## JARVIS stacks (four + SDK)

```
legacy awesome_chat ──HTTP──▶ bridges :8091/:8092   (daily)
jarvis_prod brain_pc ──MQTT jarvis/node/…──▶ agent_phone (smoke only)
jarvis_core Reflexion (dormant cognition)
root core/ safety kernel ──used by──▶ jarvis_node_sdk/pc_skills
jarvis_node_sdk ──MQTT chimera/<node>/…──▶ Brain   (active spine)
```

## Data flow (P4 intended path)

`NL → CognitivePipeline → device_intents / DeviceAgent → skill_risk_int → ApprovalStore (risk≥2) → DeviceDispatcher → signed MQTT cmd → node skill → response → audit/memory`

---

# Outstanding TODOs

## Explicit markers in Brain Python

**Almost none.** No production `TODO`/`FIXME`/`HACK`/`NotImplementedError` stubs found. Incomplete work is expressed as deferred comments, orphan modules, and planning docs.

| Location | Marker / phrase | Status |
|----------|-----------------|--------|
| `api/routes/devices.py` ~67–68 | NOTE: static `/approvals` before `/{node}` | Complete (routing guard) |
| `services/memory_service.py` ~42–44 | “future phase” scoped filtering | **Open** |
| `memory/scoping.py` ~4–6 | Foundation before multi-user enforcement | **Open** |
| `mqtt/client.py` ~21–22 | `#` wildcard deferred | **Open** |
| `identity/service.py` docstring | “Enforcement is a future phase” | **Stale** (HTTP enforces) |
| `config/config.py` ~54 | “non-enforcing” comment | **Stale** |
| `api/routes/query.py` ~29 | “non-enforcing” comment | **Stale** |
| `memory/graph_builder.py` ~3 | “Optional layer (V4+)” | **Unwired** |
| `PRIORITY-4_DEFINITION.md` ~214, 500 | Historical `TODO(auth)` refs | **Stale** (M1 removed markers) |

## JARVIS markers

| Location | Nature |
|----------|--------|
| `device_integration.py` ~10 | Abstract `NotImplementedError` on base adapter |
| Several Windows signal handlers | `NotImplementedError` fallback for `add_signal_handler` |
| Spec docs (`UI_SPEC`, `3D_ENGINE`, `VOICE_SYSTEM`) | Large TBD surfaces |

## Inferred hidden TODOs (implementation stops midway)

1. Finish M10 dashboard UI after API invoke lands.
2. Live M9 phone deployment evidence.
3. Wire or retire `tools/`, `GraphBuilder`, `Reranker`, `ModelRouter`.
4. Emit or delete unused `TokenStreamed` / `ApprovalRequested` event types.
5. Update `CURRENT_STATUS.md` and foundation docs to match P4 code.
6. Expand `test_scope_enforcement.py` to include invoke/approvals/audit routes.
7. Resolve `tools/` fate (BRAIN_V2_DESIGN “keep” vs PHASE7/8 “retire”) — deferred to P5 unless dispatch needs it (`PRIORITY-4_DEFINITION.md` §6).

---

# Missing Components

## Missing / never built

| Component | Expected by | Evidence of absence |
|-----------|-------------|---------------------|
| `sync/` journal package | V2 design | Not in tree |
| WebSocket `/v2/stream`, MCP | V2 design | Not in tree |
| Brain Mosquitto in compose | Ops convenience | `docker/docker-compose.yml` has api/ollama/frontend only |
| JARVIS CI workflows | Hygiene | No `.github/` |
| `prompts/` directories | Requested scan | Absent both repos |
| `.cursor/` project rules | Requested scan | Absent both repos |
| Dedicated `jarvis_node_sdk/requirements.txt` | Packaging | Deps only in `termux_install.sh` |
| React dashboard components | `frontend/components/README.md` | Placeholders only |

## Missing tests / thin coverage

| Area | Gap |
|------|-----|
| `tools/*`, `graph_builder.py`, `reranker.py`, `router.py` | Untested (also unused) |
| `main.py` CLI | Untested |
| Scope sweep | Missing invoke/approve/deny/audit from `test_scope_enforcement.py` |
| JARVIS legacy bridges | Minimal / skip-gated |
| Cross-repo live Tailscale E2E | Not automated |

## Dead / orphan / duplicate

| Item | Notes |
|------|-------|
| Brain `tools/` | Full impl, zero imports |
| `models/reranker.py`, `router.py` | Exported, unused |
| `memory/graph_builder.py` | Implemented, never instantiated |
| JARVIS `easytool/`, `taskbench/` | Vendored benchmarks, unused |
| JARVIS `hugginggpt/web/node_modules` | ~6195 tracked files (`.gitignore` path bug) |
| Root `package-lock.json` | Orphan empty lockfile |
| Dual MQTT grammars | `chimera/…` vs `jarvis/node/…` |
| Dual cognition | Brain pipeline vs legacy / jarvis_prod / jarvis_core |
| `core/` vs `jarvis_core/core/` | Import-path collision risk |

## Broken imports

Static analysis: **no broken internal Brain imports** detected. Import failures under system Python were third-party (`chromadb`, `aiomqtt`) when venv not active — not missing project modules.

---

# Technical Debt

Ranked from repository evidence:

1. **Legacy still carries daily load** while Chimera path is unfinished for trial (`PRIORITY-4` C2; `CURRENT_STATUS.md`).
2. **Two MQTT ecosystems** (`chimera/` vs `jarvis/node/`) — consolidation gated on P4 trial.
3. **Doc/code drift** — status docs and “non-enforcing” comments lag P1/P4 security reality.
4. **Orphan Brain modules** — `tools/`, graph, reranker/router inflate surface without value.
5. **JARVIS repo hygiene** — committed `node_modules`, orphan lockfile, no CI.
6. **`core/` naming collision** — `CURRENT_STATUS.md` L117–118.
7. **Secret rotation advisory** — previously leaked secrets purged via filter-repo; rotation status unconfirmed (`CURRENT_STATUS.md` L132).
8. **MQTT TLS / per-node ACLs** — deferred to P5; currently Tailscale-trust model.
9. **Memory multi-user scoping** — write metadata without read filter.
10. **Unresolved `tools/` design conflict** — two docs disagree; P4 deferred resolution.

---

# Risks

| Risk | Severity | Evidence |
|------|----------|----------|
| Keystone demo never run → legacy cannot retire | **Critical blocker** | ADR-014 + P4 §3; M11–M12 not started |
| Uncommitted M10 API diverges / lost | **High** | 4 dirty files on Brain; branch already ahead 4 |
| Phone node not actually live → demo fails | **High** | M9 commit labeled “software half”; no live evidence in-repo |
| Local LLM parse quality vs Claude-API legacy | **Medium–High** | P4 risk R2 in `PRIORITY-4_DEFINITION.md` ~L625 |
| Legacy `bridge_server` still ungated | **High** until trial | ADR-014 C4; SECURITY_MODEL notes |
| Dashboard without approval UI → NP-7 ops friction | **Medium** | M10 incomplete |
| Credential/HMAC misconfig → 503 spine | **Medium** | Devices routes require `mqtt_enabled` + HMAC |
| Windows asyncio / uvicorn loop footguns | **Medium** | Documented in P3 closure; mitigated in `main.py` |
| Repo bloat / hygiene in JARVIS | **Low–Medium** | node_modules in git |
| Stale comments mislead future agents | **Low–Medium** | identity/query “non-enforcing” |

---

# Recommended Completion Order

Aligned with frozen P4 plan (`PRIORITY-4_DEFINITION.md` §5):

1. **Land Brain uncommitted M10 API** (invoke + approver_keys) + tests green.
2. **Dashboard M10 UI** — invoke, approvals, audit.
3. **Finish M9 ops** — real phone on Tailscale; prove `phone.battery`.
4. **Multi-node concurrent proof** (PC + phone).
5. **M11 Keystone Demo** — checklist + trial instrumentation.
6. **Run trial** (outcome-based, not calendar-only).
7. **M12** — outcome report; ADR-014 retirements or documented deferral; `PRIORITY-4-CLOSURE.md`; refresh status docs.
8. **Only then** Priority #5 hygiene (`authority_scope`, dead code, TLS/ACLs, voice, etc.).

Do **not** shut off `awesome_chat.py` before M12 gate evidence (NP-10 / ADR-014).

---

# Estimated Completion %

Percentages are **judgment from evidence**, not measured LOC coverage.

## Overall

| Scope | Estimate | Why |
|-------|----------|-----|
| **Chimera ecosystem (vision in CLAUDE.md)** | **~48%** | Spine + skills + Brain cognition exist; daily use, voice, multi-hardware, KG, legacy retirement remain |
| **Brain repo as cognitive server** | **~72%** | V2 foundation + P1–P3 + most P4 Brain milestones; M10 WIP; deferred V2 features open |
| **JARVIS Chimera embodiment path** | **~70%** | SDK + skills + entrypoint + installer; live multi-node/trial unproven |
| **JARVIS as whole repo (all islands)** | **~40%** | Three legacy islands still active/dormant; consolidation unfinished |
| **Priority #4 specifically** | **~75% of milestones / ~55% of “done” definition** | M1–M8 code done; M9 partial; M10 mid; M11–M12 = demo + retirements = real DoD |

## By Brain module

| Module | % | Why |
|--------|---|-----|
| `api/` + auth middleware | 85% | Full REST v1; M10 invoke uncommitted; no WS |
| `core/` pipeline | 80% | Full turn + device path; no DAG planner |
| `devices/` + `mqtt/` | 90% | Spine complete; needs live MQTT config |
| `agents/` | 75% | Works; planner/critic not fully registry-driven; no real tools |
| `memory/` | 65% | Hybrid retrieval OK; scoping/graph/rerank incomplete |
| `identity/` | 80% | Scopes enforced on HTTP; comments stale; approver seed WIP |
| `events/` | 60% | Bus works; several event types unused |
| `frontend/dashboard` | 55% | Ops UI works; M10 console missing |
| `tools/` | 10% | Built but abandoned/unwired |
| `models/` reranker/router | 5% | Dead code |
| Docs / ADRs | 90% | Excellent; some stale sections |

## By JARVIS subsystem

| Subsystem | % | Why |
|-----------|---|-----|
| `jarvis_node_sdk` | 85% | Skills + caps + tests; production soak/phone live thin |
| root `core/` kernel | 90% | Fixed + tested + wired to PC skills |
| Legacy stack | 70% operational / 20% Chimera-aligned | Daily use but outside Brain |
| jarvis_prod | 45% | Built, smoke OK, not live, wrong topic namespace |
| jarvis_core | 25% | Prototype never E2E |
| Voice / web / 3D | 5–15% | Specs only or legacy-only |
| Ops (Tailscale mesh) | 40% | Docs+installer; live proof incomplete |

---

# Files Requiring Immediate Attention

| Priority | File | Reason |
|----------|------|--------|
| P0 | `Brain/api/routes/devices.py` | Uncommitted M10 `invoke` — finish & commit |
| P0 | `Brain/identity/service.py`, `config/config.py`, `api/schemas.py` | Same WIP cluster |
| P0 | `Brain/frontend/dashboard/app.js` (+ html/css) | M10 UI not started |
| P0 | `JARVIS/docs/context/CURRENT_STATUS.md` | Misleading for next session |
| P0 | Live ops: Tailscale + phone `run_chimera_node.py` | M9 gate for demo |
| P1 | `Brain/docs/PRIORITY-4_DEFINITION.md` | Governing checklist for remaining work |
| P1 | `JARVIS/run_chimera_node.py` | Production entrypoint for trial |
| P1 | `JARVIS/hugginggpt/server/awesome_chat.py` | Do-not-break until M12 |
| P2 | `Brain/tools/` | Resolve keep vs retire |
| P2 | `Brain/services/memory_service.py` | Scoped reads still future |
| P2 | JARVIS `.gitignore` / `node_modules` | Repo hygiene bomb |

---

# Evidence Appendix

## A. Git history (Brain, all commits)

```
09351c0 Priority #4 M7: Brain dispatch bridge + NP-7 approval flow
e0091b4 Priority #4 M4: capability registry (Brain side)
7a49961 Priority #4 M2: envelope correlation ID + fix response-handler accumulation
bbd74e9 Priority #4: freeze Cognitive Dispatch definition; M1 scope enforcement
e5d337f Priority #3: Complete
abc00ff Milestone Completed till 6
f676b4b Split audit artifacts out of the Decision Log into docs/audits/
7b25460 Priority 2 closure: Part 4/5 implementation readiness review and GO decision
5019880 Priority 2 closure: Part 2 summary correction + Part 3 dependency analysis
f865ac7 Restore dashboard authenticated communication with Brain (Priority 1 closure)
eda4c90 Priority 2: finalize ADR-011 through ADR-014; stop gitignoring docs/
4b72501 Priority 1: close critical security findings from the ecosystem audit
fbb7782 Add canonical Chimera ecosystem architecture reference
…
88272ed V1
```

Author: **Yash** only. Branch: `main` **ahead 4** of `origin/main`.

## B. Git history (JARVIS, P4-relevant)

```
ae60a1a Priority #4 M9 (software half): node provisioning doc + Termux installer
2f545e9 Priority #4 M8: production node entrypoint
10d4fd0 Priority #4 M6: PC skill subset through the safety kernel + operator ceiling
e6cd2ac Priority #4 M5: real phone skills on the SDK
93da948 Priority #4 M3: capability declaration (node side)
ffe9eb8 Priority #4 M2: echo request_id on command responses
6dd840f Priority #3: Complete
…
```

Branch: `main` **ahead 7** of `origin/main`. Clean tree.

## C. Uncommitted Brain diff summary

```
api/routes/devices.py | +49 (invoke endpoint)
api/schemas.py        | +5  (InvokeIn)
config/config.py      | +6  (approver_keys)
identity/service.py   | +18 (approver seeding)
```

## D. Priority #4 milestone scorecard (evidence-based)

| # | Objective | Code evidence | Live ops evidence | Verdict |
|---|-----------|---------------|-------------------|---------|
| M1 | Scope enforcement | Brain commit `bbd74e9` | N/A | **Done** |
| M2 | Correlation ID | Both repos | Fake-broker tests | **Done** |
| M3 | Node capabilities | JARVIS `93da948` | — | **Done** |
| M4 | Brain capabilities registry | Brain `e0091b4` | — | **Done** |
| M5 | Phone skills | JARVIS `e6cd2ac` + tests | Spot-check not archived | **Done (SW)** |
| M6 | PC skills + kernel | JARVIS `10d4fd0` + tests | — | **Done (SW)** |
| M7 | Dispatch + approval | Brain `09351c0` + tests | — | **Done** |
| M8 | Prod entrypoint | `run_chimera_node.py` | 24h soak not evidenced | **Done (SW)** |
| M9 | Phone deployment | Installer + docs | Hardware live **not evidenced** | **Partial** |
| M10 | Multi-node + dashboard console | Uncommitted invoke API; UI missing | Concurrent live **not evidenced** | **In progress** |
| M11 | Keystone demo + trial | Absent | Absent | **Not started** |
| M12 | Trial outcome + retirements | Absent | Absent | **Not started** |

## E. Scan coverage notes

| Area | Result |
|------|--------|
| `Brain/docs/` | Fully inventoried (PHASE, V2, audits, P4, ADRs) |
| `JARVIS/docs/` | Fully inventoried (vision, architecture, specs, context, ops) |
| `.claude/skills/` | Present both repos (10 skills); workflows/CI only on Brain |
| `.cursor/`, `prompts/` | **Absent** both repos |
| TODO/FIXME in Brain `.py` | Essentially **none** (incomplete work via docs/orphans) |
| Tests (Brain) | 38 `test_*.py` files, **223** `test_` functions counted 2026-08-02 |
| Dependency audit | Brain `requirements.txt` coherent; heavy ML (`sentence-transformers`); MQTT=`aiomqtt` only. JARVIS has **8** scattered requirements files, no unified lockfile. Unused: Brain tools/reranker path; JARVIS easytool/taskbench. Optional: Langfuse/Telegram (jarvis_prod). Outdated/conflict: not fully version-pinned; interpreter matrix 3.10/3.11/3.12 across islands. |

## F. Insufficient evidence (explicitly not guessed)

- Whether Claude vs human authored specific commits (git shows Yash only).
- Whether Nothing Phone has ever run `run_chimera_node.py` successfully on Tailscale after M9.
- Whether M5/M6 “live spot checks” were performed (tests exist; live logs not in repo).
- Rotation status of historical leaked secrets.
- Exact % of daily commands already replaceable by Chimera path (requires trial instrumentation from M11).

## G. Key governing documents (read order for resume)

1. `Brain/docs/PRIORITY-4_DEFINITION.md` — active plan  
2. `Brain/docs/audits/PRIORITY-3-EXECUTION-SPINE-CLOSURE.md` — spine guarantees  
3. `Brain/docs/DECISION_LOG.md` — ADR-011–014  
4. `Brain/docs/CHIMERA_ECOSYSTEM_ARCHITECTURE.md` — boundary law  
5. `JARVIS/docs/ops/NODE_PROVISIONING.md` — node ops  
6. This file — recovery snapshot as of 2026-08-02  

---

*End of recovery report. No source code was modified; only this document was created.*
