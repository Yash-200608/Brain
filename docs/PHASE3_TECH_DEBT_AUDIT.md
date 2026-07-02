# PHASE 3 — TECHNICAL DEBT AUDIT

> Deep technical-debt audit of the Chimera ecosystem (Brain + Jarvis).
> Date: 2026-06-14 · Status: AUDIT (no changes proposed) · Code over docs.
> Built on the Phase 1 verified module map and Phase 2 gap analysis.
> Severity = **impact**: Critical / High / Medium / Low.

## Impact ranking — top of the stack

| # | Risk | Severity | Why it tops the list |
|---|---|---|---|
| 1 | **Unauthenticated remote code execution surface** | **Critical** | `bridge_server.py` exposes shell/file/shutdown over HTTP on `0.0.0.0`; `awesome_chat.parse_device_command` prompts the LLM to *never refuse* destructive actions. |
| 2 | **Security perimeter = "hope env is set"** | **Critical** | Brain auth is non-enforcing (owner+ALL_SCOPES, CORS `*`); Jarvis tokens & `JARVIS_HMAC_KEY` default to `""`. Open by default. |
| 3 | **The mitigating safety layer is dead code** | **High** | `JARVIS/core/` (idempotency/validation/sandbox/undo/risk) is fully built + tested but wired to nothing; live executors bypass it. |
| 4 | **Four orchestrators, 3+ memory stores, large dead zones** | **High** | Source-of-truth ambiguity + maintenance drift across both repos. |
| 5 | **SPOFs with no replication/backup** | **High** | MQTT broker, single Brain process, SQLite/Chroma all single-instance. |
| 6 | **Scale ceilings baked in** | **Medium** | Single uvicorn worker, singletons-at-import, no DB indexes, unbounded `jobs.db`. |
| 7 | **Over-built unused foundation vs under-built live path** | **Medium** | Effort spent on non-enforcing multi-user infra while the active device path is unsafe. |

---

## DELIVERABLE 1 — Technical Debt Report (synthesis)

The debt has a clear shape: **the codebase is wide, not deep.** Multiple complete
implementations of the same capability sit side by side, the most robust ones are
often the *unused* ones, and the parts that are actually live are the least
hardened. Concretely:

- **Effort is mislocated.** The best-engineered code in the system — Brain's V2
  foundation (identity, envelope, eventbus, scoping, model gateway) and Jarvis's
  `core/` safety pipeline — is either non-enforcing or not wired in. The code
  that runs in anger (`awesome_chat`, `bridge_server`, `brain_pc`) is the least
  guarded.
- **Three parallel "framework" investments** were made and largely abandoned:
  Brain `tools/`, Jarvis `jarvis/` (clean skill/router framework), Jarvis
  `core/` (safety executor). All complete, all dead.
- **No integration debt is being paid** — the product premise (Jarvis ⇄ Brain)
  has zero code, so every subsystem re-implements what it needs locally.

Debt is therefore dominated by **duplication + dead code (maintainability)** and
**unhardened live paths (security)**, not by missing features.

---

## DELIVERABLE 2 — Dead Code Inventory

### Brain

| Item | Path | Evidence |
|---|---|---|
| Knowledge graph | `memory/graph_builder.py` | `GraphBuilder` never imported/instantiated; nothing builds triples. |
| Cross-encoder reranker | `models/reranker.py` | Only re-exported; never instantiated/called. |
| Model router | `models/router.py` | `ModelRouter()` never constructed; `.pick()` never called (and maps all → same model). |
| **Entire tools layer** | `tools/{base,system_tools,api_tools,memory_tools}.py` | `Tool`, `ToolRegistry`, `SystemInfoTool`, `HTTPGetTool`, `MemorySearchTool`, `MemoryWriteTool` imported only within `tools/`. No agent/pipeline/route uses it. |
| Unused schema | `api/schemas.py` `HealthOut` | `/health` returns a plain dict; `HealthOut` referenced nowhere. |
| Aspirational UI | `frontend/components/` | README lists React components that don't exist; real dashboard is vanilla JS. |
| Dead protocol surface | `protocols/envelope.py` `EnvelopeType` | `TURN_SUBMIT/TASK_ASSIGN/TASK_PROGRESS/APPROVAL_GRANTED/APPROVAL_DENIED` have no `Event` subclasses. |
| Dead agent fields | `agents/protocol.py` | `AgentStatus.BLOCKED/ERROR` never set; `AgentResult.metadata`/`events` never populated. |
| Unused protocol conformance | `agents/planner.py`, `agents/critic.py` | Both subclass `Agent.run()` but are only ever called via bespoke `plan()`/`review()`; not registered. |
| Duplicate logger | `main.py:14` | Defines its own `configure_logging`, shadowing `logs/logger.py`. |
| Unused package surface | `core/__init__.py` | Zero `from core import …` consumers (submodules imported directly). |

### Jarvis

| Item | Path | Evidence |
|---|---|---|
| **Entire safe-execution layer** | `JARVIS/core/*` | `execute_task` called only by 3 test files; no app/CLI/server imports it. |
| LRU context store | `JARVIS/core/memory.py` | `get_context/set_context` never imported anywhere. |
| Undo (runtime half) | `JARVIS/core/undo.py` | `undo_last_action()` never invoked at runtime (only `record_action`). |
| **Entire `jarvis/` framework** | `hugginggpt/server/jarvis/*` | Nothing constructs `MQTTRouter`; `state.py` unused even within the package. |
| Conversation memory | `hugginggpt/server/memory_module.py` | Only imported by `test_jarvis.py`; `awesome_chat` never imports it. |
| Structured logging | `hugginggpt/server/logging_utils.py` | Never imported; `awesome_chat` rolls its own formatter. |
| Unreachable branch | `models_server.py` | `if model_id == 'A' and model_id == 'B'` (always False). |
| Dead handlers | `models_server.py` | Handlers for pipelines commented out in `load_pipes`. |
| Latent crash / unused | `run_gradio_demo.py` | `uuid.uuid4()[:4]` (slices a UUID object) → `TypeError` if branch runs. |
| Broken tests (red) | `test_jarvis.py` | Imports `phone_bridge.RateLimiter`, `awesome_chat.is_high_risk_request`/`has_explicit_confirmation` — none exist. |
| Unused imports | `brain.py` (`OllamaError`), `executor.py` (`SandboxViolation`), `claude_adapter.py` (`re`), `jarvis/*` (os/time/shutil/sys) | Confirm modules aren't linted/exercised. |
| Dead methods | `ollama_client.mark_used()`, `transport.iter_messages()` | Defined, never called. |

---

## DELIVERABLE 3 — Duplication Inventory

| Capability | Implementations (count) | Locations |
|---|---|---|
| **Orchestration / cognitive loop** | **4 (+1 in Brain)** | `jarvis_core/core/brain.py`, `jarvis_prod/brain_pc.py`, dead `jarvis/router.py`, `awesome_chat.py`; Brain `core/pipeline.py`. |
| **Planner→Critic retry loop** | **3** | Brain `agents/` (Planner+Critic), `jarvis_core/brain.py` (llama3/mistral), `jarvis_prod` (Reflector failure counter). |
| **Memory / state stores** | **5** | Brain Chroma `jarvis_memory`; jarvis_core Chroma `brain/chroma`; jarvis_prod `jobs.db`; dead `memory_module` deque; Brain `api/routes/memory.py` spins a **2nd** Chroma separate from the orchestrator's. |
| **Wire protocol / schema** | **3** | Brain `protocols/envelope.py`, `jarvis_prod/protocol.py`, `jarvis/schema.py` (schema drift). |
| **Phone control surface** | **4** | `phone_bridge.py` (ADB), `phone_agent.py` (relay), dead `jarvis/phone_skills.py`, `jarvis_core/agent/phone_executor.py`. |
| **HMAC signing** | **2** | `jarvis_core/core/signing.py` and an inline copy in `agent/phone_executor.py`. |
| **Voice (STT/TTS/wake-word)** | **2** | `voice_io.py` (in-proc lib) and `voice_module.py` (standalone HTTP). |
| **Skill catalog (names)** | **3** | `jarvis/pc_skills.py`, `jarvis/phone_skills.py`, `brain_pc._known_skills`. |
| **Logging config** | **2** | Brain `main.py` inline vs `logs/logger.py`. |
| **Model cache pattern** | **2** | `models/embeddings.py` and `models/reranker.py` (identical double-checked-lock). |
| **Live orchestrator instances** | **2** | Brain CLI `_orch` vs API `_orch` — separate, non-shared. |

---

## DELIVERABLE 4 — Security Review

> Secrets are **env-based** (good) — no hardcoded production secrets on the live
> path. The risk is **open defaults** + **arbitrary execution**, currently
> mitigated *only* by running everything behind Tailscale and setting env vars
> correctly. The defaults fail open, not closed.

### Authentication

| Finding | Severity | Evidence |
|---|---|---|
| Brain API has no enforced auth | **High** | `AuthMiddleware` never rejects; `default_principal()` = owner with `ALL_SCOPES`; CORS `allow_origins=["*"]`. |
| Bridge/relay tokens default empty | **High** | `os.environ.get("RELAY_TOKEN", "")`, `BRIDGE_TOKEN` unset ⇒ `""`. If env missing, auth is effectively off. |
| Per-device key model designed, not enforced | Medium | Brain `api_keys` default `{}`; identity is resolve-only. |

### Secrets

| Finding | Severity | Evidence |
|---|---|---|
| `JARVIS_HMAC_KEY` defaults to `""` | **High** | `config.py:130`. Empty key ⇒ zero-trust MQTT signatures are forgeable; the whole replay/tamper defence depends on this one env var. |
| Placeholder token in docs | Low | `phone_bridge.py:13` example `"your-secret-token"` (doc only, not a real secret). |

### Remote execution

| Finding | Severity | Evidence |
|---|---|---|
| Full RCE over HTTP | **Critical** | `bridge_server.py`: `run_command`/`run_command-with-shell`, file read/write/delete, `kill_process`, `shutdown`/`restart`, bind `0.0.0.0`, single Bearer token. |
| LLM told to never refuse destructive ops | **Critical** | `awesome_chat.parse_device_command` system prompt: never refuse, never confirm, execute delete/shutdown/wipe/kill with "pre-authorization". Prompt-injection → device takeover. |
| Brain pre-check misses `run_shell` args | Medium | `jarvis_core` brain `_plan_passes_sandbox` validates `path/cwd/file/src/dst` keys but not `cmd`; shell args aren't path-sandboxed before dispatch. |
| Arbitrary shell skills | Medium | `jarvis/pc_skills.py` `pc.shell.run` runs verbatim input (in the dead framework, but reflects intent). |

### MQTT / device communication

| Finding | Severity | Evidence |
|---|---|---|
| Phone responses unsigned | Medium | `jarvis_core`: only inbound commands HMAC-verified; replies on `jarvis/phone/state` correlated by `request_id` only → response spoofing. |
| No MQTT TLS in code | Medium | Encryption relies entirely on Tailscale; if broker is reachable off-Tailscale, traffic + weak auth are exposed. |
| Relay/agent execute arbitrary Android actions | Medium | `phone_agent.py` runs termux/`am`/`input`/`dumpsys`; a compromised relay can drive the phone. |

### APIs

| Finding | Severity | Evidence |
|---|---|---|
| CORS wildcard + no auth (Brain) | High | `api/server.py` `allow_origins/methods/headers = ["*"]`. |
| Services bind all interfaces | Medium | `relay_server`, `phone_relay_bridge`, `bridge_server` default `0.0.0.0`. |

---

## DELIVERABLE 5 — Scalability Review

| Risk | Severity | Evidence / mechanism |
|---|---|---|
| Single uvicorn worker by design | Medium | EventBus + SessionActors are in-process; scale-out only via sticky-session routing (documented, not built). |
| Heavy singletons at import | Medium | Every Brain route module builds its store/orchestrator at import; can't fan out workers without duplicating state (and the 2nd Chroma). |
| Rate limiter not shared | Medium | `RateLimitMiddleware` is per-process per-IP; meaningless across workers. |
| No DB indexes | Medium | `logs.turns(session_id)`, `goals(status)` rely on table scans. |
| `jobs.db` unbounded | Medium | `JobLog(capacity=200)` stored but never used to prune; SQLite grows forever. |
| Eviction best-effort | Low | `SessionManager` can exceed `max_sessions` transiently if all actors busy. |
| In-memory RPC correlation | Medium | `brain_pc`/`jarvis_core` correlate MQTT replies via in-RAM Futures — lost on restart; no durable queue. |
| Embedded Chroma ×N | Medium | Multiple separate Chroma instances; no shared vector service; model load is heavy on first use. |
| Session capture lossy | Low | `logs/store` `INSERT OR IGNORE` keeps only first turn's `user_input` at session level. |

---

## DELIVERABLE 6 — Architectural Risk Assessment (incl. SPOFs)

### Single points of failure

| Layer | SPOF | Blast radius |
|---|---|---|
| **Brain** | One uvicorn process; one in-process EventBus; module-level singletons | Process death loses all in-RAM session working state (episodic persists). One bad import at module load kills the whole API. CLI and API run *separate* orchestrators — no shared state. |
| **Jarvis** | `brain_pc` / `jarvis_core` are single processes each | Brain-node death stops all command dispatch; mitigated only by phone heartbeat + `NEED_ATTENTION.md`. |
| **Communication** | **MQTT broker** (PC-hosted) and **relay_server** | Broker down ⇒ entire nervous system down (no node can be commanded). Relay down ⇒ relay-mode phone control down. No failover (cloud replica is future/manual). |
| **Storage** | SQLite single-writer (`goals.db`, `sessions.db`, `jobs.db`), JSON `.executed_ids.json`, embedded Chroma | No replication, no configured backup. Idempotency JSON is corruptible (there is a test for a corrupted store). |

### Over-engineering (complexity with little current value)

- Brain V2 foundation: `identity/` (non-enforcing), `protocols/Envelope` (no peer consumes it), `events/` (token-stream/approval events defined, unwired), `memory/scoping` (filter off), `modelgw` provider registry (one provider). Justified as roadmap groundwork, but currently complexity without a consumer.
- `tools/` (Brain), `jarvis/` framework, and `JARVIS/core/` safety layer — three complete subsystems with zero runtime use.
- `models/router.py` — an abstraction that resolves every input to the same model.

### Under-engineering (needs stronger architecture)

- **Integration layer** between Brain and Jarvis — the product premise — does not exist.
- **Live device safety**: arbitrary shell over HTTP + "never refuse" LLM, while the robust safety executor sits unused.
- **Error semantics**: failed LLM → silent `OK` empty output (Brain agents); critic silently gives up after retries.
- **Observability**: no metrics endpoint, no structured request tracing in the live path.
- **Brain multi-tenancy**: auth/scoping are scaffolding; real isolation absent.

### Risk-prioritized remediation order (for later phases — not actioned here)

1. Close the RCE/auth defaults (fail-closed tokens, enforce Brain auth, gate destructive ops). *(Critical)*
2. Wire the existing `JARVIS/core/` safety executor into the live device path. *(High — reuses built code)*
3. Pick **one** orchestrator, **one** memory owner, **one** wire protocol; retire the rest. *(High — kills most duplication + dead code at once)*
4. Add storage indexes/backups; bound `jobs.db`; durable RPC correlation. *(Medium)*
5. Build the Brain↔Jarvis integration the vision requires. *(architectural; Phase 4+)*

> Reminder: this audit only *identifies and prioritizes* debt. No code was
> changed and no remediation was performed.
