# Chimera Ecosystem — Decision Log

This is the ecosystem-level ADR log — decisions that govern both the Brain and JARVIS repositories, not either repo's internal implementation choices. It exists per **ADR-012** below, which resolves the documentation-ownership question raised during Priority #2.

Numbering continues from JARVIS's own `docs/context/DECISION_LOG.md` (ADR-001–ADR-010, JARVIS-internal decisions), starting at **ADR-011** — the entry JARVIS's log left as a placeholder pending this decision. JARVIS's log now points here for ADR-011 onward rather than duplicating it. JARVIS-repo-internal decisions (e.g., which library, which file gets renamed) continue to be logged in JARVIS's own file, not here.

Each entry: Context, Problem Statement, Decision, Alternatives Considered, Trade-offs, Consequences, Implementation Impact, Migration Strategy (if applicable), Future Reconsideration Criteria.

---

## ADR-011: Brain Is the Sole Cognitive Authority; JARVIS Is the Embodiment Platform

**Status:** Accepted · **Owner:** Yash (sole maintainer, both repos) · **Date:** 2026-07-02
**Depends on:** none · **Supersedes:** the placeholder ADR-011 in `JARVIS/docs/context/DECISION_LOG.md` · **Review trigger:** Brain internally decomposes into multiple cognitive services, or a demonstrated hard-real-time need emerges that the locally-sovereign mechanism (§4b below) can't cover.

### Context
Four independent implementations had each embedded planning/memory logic at some point: the JARVIS legacy stack (`awesome_chat.py`, cloud-LLM NL parsing, daily production use), `jarvis_prod/brain_pc.py` (embedded orchestrator, never live), `jarvis_core/brain.py` (Planner/Critic/Executor loop, never completed a correct run — a signing-order bug guarantees every exchange fails verification), and Brain's own `core/pipeline.py` (the only one that actually runs). Two independent, mutually unaware planning efforts had proposed different physical homes for "the Brain": Brain's own `PHASE7_CHIMERA_V2_BLUEPRINT.md`/`PHASE8_IMPLEMENTATION_ROADMAP.md` (2026-06-14, audited both repos, concluded Brain-repo-as-hub) versus JARVIS's `SYSTEM_ARCHITECTURE.md`/`BRAIN_SPEC.md` (2026-07-01, audited only JARVIS, proposed building a Brain inside the JARVIS repo with no awareness the Brain repo existed). A six-dimension evaluation (correctness, maintainability, security, extensibility, observability, sustainability) found Brain ahead on four, tied on one (security — both sides insecure, differently), even on one.

### Problem Statement
Which component may plan, remember, and decide, and which must only sense, act, and enforce safety at the point of action — and where does that authority physically live?

### Decision
The standalone Brain repository is the sole cognitive authority for a Chimera deployment: it owns memory (all tiers), planning, agent orchestration, goal state, reflection, and identity/authorization policy. JARVIS is the reference embodiment platform: device/OS integration, interaction surfaces (voice, UI, chat), and safety-gated execution — it never originates multi-step plans. The full boundary model, the functional cognition/embodiment test, actor definitions, local-autonomy rules, the communication-contract shape, the trust invariants, deployment topologies, and the versioning strategy are specified in [`CHIMERA_ECOSYSTEM_ARCHITECTURE.md`](CHIMERA_ECOSYSTEM_ARCHITECTURE.md) §1–§9, adopted here by reference. This ADR is the decision record; that document is the specification — content lives in one place, not both.

### Alternatives Considered
1. **Build Brain inside the JARVIS repo** (JARVIS's own `SYSTEM_ARCHITECTURE.md` plan, merging `jarvis_prod` + `jarvis_core` + root `core/`) — rejected: creates a fourth cognition stack next to the one that already runs; ignores that Brain wins decisively on 4 of 6 evaluated dimensions.
2. **Symmetric peer cognition** (both repos keep independent planning, reconciled via sync) — rejected: doesn't resolve the fragmentation that caused the four-implementations problem; adds reconciliation complexity with no demonstrated need.
3. **Merge both repos into one codebase** — rejected: different release cadences, dependency footprints, and deployment targets; no evidence a monorepo reduces an ownership problem that isn't a repo-boundary problem.

### Trade-offs
JARVIS cannot make multi-step decisions independently — every non-trivial action requires a live or bounded-autonomy-cached round trip to Brain. This trades local independence for eliminating duplicate, unreconciled reasoning, which the four-implementations history shows is the more expensive failure mode in practice (one of the four never worked at all; another is a live security risk specifically because it embeds unchecked cognition).

### Consequences
`jarvis_core`'s Planner/Critic/Executor loop and `brain_pc.py`'s embedded orchestration are retired as cognition (disposition and timeline: ADR-014). Their non-cognitive parts — `transport.py`, `signing.py`, `sandbox.py`, `phone_executor.py` — are extracted as the JARVIS-owned node SDK. JARVIS's `SYSTEM_ARCHITECTURE.md`, `BRAIN_SPEC.md`, `BRAIN_CONSTITUTION.md`, `AGENT_ARCHITECTURE.md`, and `MEMORY_ARCHITECTURE.md` are superseded at the ownership-boundary level (already marked accordingly in `SYSTEM_ARCHITECTURE.md`); their file-level audits remain valid implementation guidance, not architecture.

### Implementation Impact
Priority #3 (execution spine) must not introduce any new planning/memory capability on the JARVIS side. Priority #4's keystone demo must originate all planning from Brain. Any future embodiment platform besides JARVIS inherits this same restriction by construction (`CHIMERA_ECOSYSTEM_ARCHITECTURE.md` §9).

### Migration Strategy
See ADR-014 (Legacy Implementation Handling & Deprecation) for the component-by-component disposition and sequencing.

### Future Reconsideration Criteria
Reopen only if Brain is decomposed into multiple internal cognitive services in a way that stops fitting the "authority boundary, not a process" framing already accommodated by `CHIMERA_ECOSYSTEM_ARCHITECTURE.md` §1, or if a demonstrated hard-real-time need exceeds what the locally-sovereign safety-action mechanism (§4b) can cover.

---

## ADR-012: Documentation Ownership — Topic-Based Split, Not Repo-Based

**Status:** Accepted · **Owner:** Yash · **Date:** 2026-07-02
**Depends on:** ADR-011 · **Supersedes:** none (informal prior discussion in-conversation, never recorded) · **Review trigger:** a third repository or embodiment platform joins the ecosystem.

### Context
Two independent documentation trees emerged with zero mutual awareness of each other (Brain's `BRAIN_V2_DESIGN.md`/PHASE2–8 series vs. JARVIS's `SYSTEM_ARCHITECTURE.md`/`BRAIN_SPEC.md`/etc.) — this is the same fragmentation pattern ADR-011 addresses for code, recurring at the documentation layer. An initial proposal to make Brain the owner of *all* ecosystem documentation was refined, on review, to a split by topic rather than by repository.

### Problem Statement
Given both repos will keep producing documentation, which repository is the source of truth for which *category* of document, so the fork that already happened once doesn't recur?

### Decision
- **Brain owns:** ecosystem/ADR-level architecture (this log, `CHIMERA_ECOSYSTEM_ARCHITECTURE.md`), cognition-domain design (memory, planning, agents, reflection), product/research vision for the cognitive platform, and the cross-repo protocol/contract specification.
- **JARVIS owns:** its own runtime implementation docs, device/hardware integration specifics, its API/service specifics (voice, UI, computer control), deployment/ops runbooks for the embodiment platform, and its own file-level technical-debt/audit tracking.
- **Cross-reference, never duplicate:** a doc that needs to state an ecosystem-level fact links to the owning repo's doc rather than restating it (the pattern already used in `SYSTEM_ARCHITECTURE.md`'s supersession note).
- **ADRs specifically:** ecosystem-scoped ADRs are logged here, in Brain, continuing JARVIS's numbering from ADR-011 onward. JARVIS's own log remains the record for JARVIS-internal decisions.

### Alternatives Considered
1. **Brain owns all docs** (the initial proposal) — rejected: JARVIS's implementation-specific docs (hardware, deployment, its own API surface) have no natural home in a cognition-focused repo and would force Brain's maintenance to track JARVIS-internal detail irrelevant to Brain's own evolution.
2. **Fully independent trees, no cross-reference rule** — rejected: this is the status quo that caused the original fork.
3. **A third, shared docs repository** — rejected: adds a repository and tooling overhead disproportionate to what is fundamentally a naming/placement convention.

### Trade-offs
A topic-based split requires judgment at the margin (e.g., "hardware integration" touches both Brain's device-registry design and JARVIS's hardware runbooks) — accepted because the alternative (strict repo-based ownership) already produced a worse outcome once.

### Consequences
`Brain/docs/DECISION_LOG.md` (this file) is a new document — necessary because no existing file was scoped for ecosystem-level ADRs; `docs/` was also removed from Brain's `.gitignore` in the same change, since an untracked "source of truth" isn't one. No retroactive reorganization of existing docs is required or performed.

### Implementation Impact
Future ecosystem-scoped ADRs (Priority #3 onward) are logged here. JARVIS-repo-internal implementation decisions stay in JARVIS's own log.

### Migration Strategy
None — this is a going-forward convention, not a retroactive reorganization.

### Future Reconsideration Criteria
If a third repository or embodiment platform joins the ecosystem, revisit whether "Brain owns ecosystem docs" still holds or whether a genuinely neutral location becomes warranted.

---

## ADR-013: Wire Protocol & Topic Namespace

**Status:** Accepted · **Owner:** Yash · **Date:** 2026-07-02
**Depends on:** ADR-011 · **Supersedes:** none · **Review trigger:** Priority #3 implementation reveals the chosen grammar can't carry a requirement `CHIMERA_ECOSYSTEM_ARCHITECTURE.md` §5 already states (e.g. per-connection versioning, capability declaration).

### Context
CLAUDE.md mandates `chimera/<node>/<action>`; nothing implements it. The only implemented, smoke-tested grammar is `jarvis_prod/protocol.py`'s `jarvis/node/{id}/{verb}` (cmd/response/event/presence/state/heartbeat), independently selected by both my audit and Brain's own `PHASE5_HARDWARE_INTEGRATION.md` as "the standard to adopt" purely because it's the only tested option. A separate, dead schema (`hugginggpt/server/jarvis/schema.py`) adds a `catalog`/`Request`/`broadcast` concept absent from the shipping protocol. This was explicitly deferred out of `CHIMERA_ECOSYSTEM_ARCHITECTURE.md` §5 as needing "a dedicated ADR," and requested as such twice in review.

### Problem Statement
Which topic grammar and envelope-signing baseline governs Brain↔node communication, given CLAUDE.md's mandate conflicts with the only implemented option, and given the ecosystem must accommodate future embodiment platforms besides JARVIS (`CHIMERA_ECOSYSTEM_ARCHITECTURE.md` §9 — a second platform is "a peer, not a special case")?

### Decision
- **Topic grammar:** `chimera/<node>/<verb>` — CLAUDE.md's original, ecosystem-neutral mandate, not `jarvis/node/{id}/{verb}`. The message *shape* (verb set: cmd/response/event/presence/state/heartbeat; correlation-id-based request/response matching) is adopted from `jarvis_prod/protocol.py` as-is, since that part is proven — only the top-level namespace token changes.
- **Envelope signing:** HMAC-with-nonce-and-skew-window (`jarvis_core/core/signing.py`'s model), not Brain's current unsigned `Envelope` — already decided in `CHIMERA_ECOSYSTEM_ARCHITECTURE.md` §5; restated here as it's the other half of "the contract."
- **Risk taxonomy:** one enum, v1 baseline = JARVIS root `core/risk.py`'s existing three tiers (low/medium/high, fail-closed-to-high on unknown), extended later per §8's enum-addition rule (all consumers must fail-closed on unrecognized values before an addition is non-breaking). Where the schema package physically lives is Priority #3 implementation detail, not decided here.
- **Broker:** Mosquitto, bound to the Tailscale interface — not a fresh decision; every prior planning document (CLAUDE.md, `jarvis_prod`, Brain's blueprint) already converges on this without disagreement.

### Alternatives Considered
1. **Adopt `jarvis/node/{id}/{verb}` as-is** (already built, zero switching cost today) — rejected: bakes a single embodiment platform's name into a protocol §9 explicitly designs to serve future non-JARVIS platforms as peers; the "it's already built" argument is weak specifically because *nothing has ever run live* on it, so the rename cost is at its lowest possible point right now and only rises later.
2. **Keep `jarvis/schema.py`'s richer shape** (adds `catalog`/`Request`/`broadcast`) as the base instead of `protocol.py` — rejected: `schema.py` has never executed at all and has already drifted from the shipping protocol; `protocol.py`'s shape is the one actually validated by `_smoke.py`.
3. **Invent a new grammar from scratch** — rejected: no evidence the existing verb set is inadequate; changing more than the namespace token would be redesigning without cause.

### Trade-offs
Renaming `jarvis/*` to `chimera/*` costs a mechanical find-replace across code that has never run live — cheap now, and only gets more expensive the longer it's deferred. Accepted as worth doing now rather than carrying a JARVIS-specific name into a protocol meant to outlive any single embodiment platform.

### Consequences
`jarvis_prod/protocol.py` and the dead `jarvis/schema.py` are merged and renamed under the new grammar as part of Priority #3, not before (no code changes in this ADR itself). `jarvis_core`'s separate `jarvis/phone/*` topic namespace is retired, not migrated (superseded by the unified grammar).

### Implementation Impact
Priority #3 owns: the actual schema/package for the envelope + risk enum, the `chimera/*` rename across `protocol.py`, the merge with `schema.py`'s useful additions (`catalog`), and reviving `hugginggpt/server/jarvis/*` as the skill/HAL catalog under the new grammar.

### Migration Strategy
Mechanical rename, done once, during Priority #3 — no live traffic exists yet on the old namespace, so there is no phased-cutover requirement.

### Future Reconsideration Criteria
If Priority #3 finds the verb set or correlation model inadequate for a requirement already stated in `CHIMERA_ECOSYSTEM_ARCHITECTURE.md` §5 (capability declaration, per-connection versioning), revisit the grammar — but the namespace token itself (`chimera/`) should not need to change again absent a change to ADR-011.

---

## ADR-014: Legacy Implementation Handling & Deprecation

**Status:** Accepted · **Owner:** Yash · **Date:** 2026-07-02
**Depends on:** ADR-011 · **Supersedes:** the general "archive, don't delete" principle stated informally in JARVIS's `SYSTEM_ARCHITECTURE.md` §5.2 (formalizes it with a concrete disposition table) · **Review trigger:** Priority #4's keystone demo reaches a defined trial-period outcome.

### Context
ADR-011 retires JARVIS-side cognition. Four cognition implementations and several already-dead modules exist and need an explicit fate, not just a general "retire eventually" principle. Brain's own `PHASE3_TECH_DEBT_AUDIT.md` already found dead modules unrelated to the cognition question at all.

### Problem Statement
What specifically happens to each existing implementation component — kept as infrastructure, retired-but-preserved, or deleted — and on what timeline?

### Decision

| Component | Disposition | Rationale |
|---|---|---|
| `jarvis_core/core/{brain.py, memory.py, scheduler.py}` (planner/critic/memory/knowledge-graph) | **Retire** — git-tag `jarvis_core-v1-cognition`, stop maintaining, do not delete | Cognition per ADR-011; never completed a correct run |
| `jarvis_core/core/{transport.py, signing.py, sandbox.py}` + `jarvis_core/agent/phone_executor.py` | **Keep — extract as the JARVIS node SDK** | Best MQTT/signing/sandbox code in the ecosystem per audit; not cognition |
| `hugginggpt/server/jarvis_prod/brain_pc.py` (embedded orchestration) | **Retire**, same tag policy | Cognition per ADR-011 |
| `hugginggpt/server/jarvis_prod/{protocol.py, jobs.py, telegram_gateway.py, scheduler.py}` | **Keep — migrate to the ADR-013 namespace** | Transport/scheduling/notification infra, not cognition |
| `hugginggpt/server/awesome_chat.py` (`parse_device_command`) | **Retire on a schedule** — stays in production until Priority #4's keystone demo has run for a defined trial period and demonstrably replaced its most-used daily commands | Only working end-to-end system today; cutting it before a replacement exists leaves zero working system. Adopts JARVIS's own already-stated position, not a new one. |
| `hugginggpt/server/bridge_server.py` | **Keep short-term**, superseded once JARVIS root `core/`'s safety kernel is wired per `CHIMERA_ECOSYSTEM_ARCHITECTURE.md` §6.5 | Same trial-period logic as `awesome_chat.py`; Priority #1's confirmation gate applies until then |
| `hugginggpt/server/jarvis/*` (`pc_skills.py`, `phone_skills.py`, `router.py`, `schema.py`, `skills.py`, `state.py`) | **Revive as the skill/HAL catalog** (per Brain's `PHASE5` recommendation, independently corroborated) | Only real dynamic-capability-discovery mechanism found anywhere; currently dead, becomes load-bearing under the new spine |
| `easytool/`, `taskbench/` | **Remove or properly attribute** | Vendored academic benchmarks, zero integration; JARVIS's own already-flagged low-priority hygiene item, unrelated to the Brain question |
| Brain `models/{reranker.py, router.py}`, `memory_module.py`, `logging_utils.py`, `tools/` | **Delete**, not retire | Confirmed dead by Brain's own audit before this ADR series began; never wired to anything; nothing to preserve |

**General policy going forward:** retire (git-tag, stop maintaining, leave in place or move to an `archive/` path) rather than delete, unless a component was already dead-on-arrival with zero production history — those may simply be deleted.

### Alternatives Considered
1. **Delete all four superseded cognition implementations immediately** — rejected: destroys the historical record (JARVIS's own `DECISION_LOG.md` explicitly prizes evidence-preservation over convenience) and risks losing not-yet-extracted reusable code (transport/signing/sandbox).
2. **Keep everything running in parallel indefinitely** — rejected: the status quo ADR-011 exists to end.
3. **Immediate cutover of `awesome_chat.py`/`bridge_server.py`** — rejected: no replacement exists yet; would leave zero working production system.

### Trade-offs
Keeping the legacy stack running during the transition means its broader attack surface (Priority #1-hardened, but still larger than the target architecture) persists longer than ideal. Accepted because an abrupt cutover with no working replacement is strictly worse.

### Consequences
Someone (the maintainer) must actually perform the git-tag-and-freeze step for `jarvis_core`'s and `brain_pc.py`'s cognition modules and the deletions listed above — this ADR decides the fate, it does not execute it. Listed explicitly as immediate next implementation work in the Priority #2 summary.

### Implementation Impact
Priority #3 must extract the node SDK from `jarvis_core` *before* its cognition half is tagged-and-frozen (extraction first, freeze after — not the reverse, or the SDK code becomes harder to find). Priority #3 also owns reviving the `jarvis/` skill framework under the ADR-013 namespace.

### Migration Strategy
Sequenced as the table above; no component is deleted or tagged by this ADR itself — this document is the decision, the git operations are follow-up implementation work.

### Future Reconsideration Criteria
Revisit the `awesome_chat.py`/`bridge_server.py` retirement timeline once Priority #4's keystone demo has an actual trial-period outcome (success/failure data), not speculatively.

---

## Architectural Decision Summary — Priority #2 Closure

**ADRs completed:** ADR-011 (Brain/JARVIS cognition-embodiment boundary), ADR-012 (documentation ownership), ADR-013 (wire protocol & topic namespace), ADR-014 (legacy implementation handling & deprecation). All four owned by Yash, dated 2026-07-02.

**Open architectural questions:** No blocking architectural ambiguities remain. The remaining open questions concern implementation, future capabilities, and deferred design work rather than foundational architecture.

**Decisions intentionally deferred:** the T2 federation/handoff protocol mechanics (`CHIMERA_ECOSYSTEM_ARCHITECTURE.md` §7 names the primitives, doesn't design the protocol); the concrete envelope JSON schema and risk-taxonomy package location (ADR-013 sets the v1 baseline, not the artifact); Brain's security-foundation rebuild scope (flagged as a tie, not a pass, in the Priority #1 six-dimension evaluation — Priority #3 scope); the specific locally-sovereign safety-action list (§4b, populated when a concrete need exists).

**Implementation work that should begin immediately after Priority #2:** extract the JARVIS node SDK from `jarvis_core` before any tag-and-freeze step (ADR-014 ordering); git-tag and freeze `jarvis_core`'s and `brain_pc.py`'s cognition modules; delete Brain's confirmed-dead modules; build the `chimera/*` envelope schema and risk-taxonomy package (Priority #3 proper); revive `hugginggpt/server/jarvis/*` as the skill/HAL catalog. **Superseded by Part 3's dependency analysis below** — several of these are not yet safe to execute as originally worded; see the corrected classifications and migration steps.

---

## Part 3 — ADR-014 Dependency Analysis (Priority #2 Closure)

Performed before any cleanup, per explicit instruction: no deletion, archival, or extraction has occurred as a result of this analysis. Nine parallel audits, each checking source references, tests, docs, ADR references, build scripts, tooling, runtime config, startup paths, imports, and generated code/automation across **both** repositories — not assuming ADR-014's original table was correct, verifying it. It found one factual error in ADR-014 itself and several dispositions that need to change from "act now" to "requires migration first." Corrections below supersede the ADR-014 table where they conflict; ADR-014's text is left as the historical record of the original decision, not rewritten.

### Final classifications

| Candidate | ADR-014 said | Verified classification | Why it changed (or didn't) |
|---|---|---|---|
| `jarvis_core/core/{brain.py, memory.py, scheduler.py}` | Retire | **Safe to archive** | Confirmed: zero external references anywhere in either repo; filesystem evidence independently confirms it never ran (no `brain/chroma/`, template-only `knowledge_graph.md`, no `.env`). Matches ADR-014, with one nuance below. |
| `jarvis_core/core/{transport.py, signing.py, sandbox.py}` + `phone_executor.py` | Keep — extract as node SDK | **Requires migration first** | Real, tested, used code — but `sandbox.py` is imported by `brain.py` (a retire candidate), so extraction must happen before archiving the cognition files, not after. A confirmed, still-unfixed bug exists: `signing.py` signs the envelope before `transport.py` injects `request_id`, so every signed phone command fails verification. Extracting this as-is would ship a broken RPC layer. |
| `hugginggpt/server/jarvis_prod/brain_pc.py` | Retire | **Requires migration first** | `_smoke.py` — the only integration test either repo has — does `from brain_pc import Brain`. Tagging/freezing this file today breaks the one thing that currently passes. `run_jarvis.ps1`'s prod path also execs it directly. |
| `hugginggpt/server/jarvis_prod/{protocol.py, jobs.py, telegram_gateway.py, scheduler.py}` | Keep — migrate to ADR-013 namespace | **Requires migration first** | Live, load-bearing, imported by both production entrypoints (`brain_pc.py`, `agent_phone.py`) and exercised by `_smoke.py`. "Keep indefinitely" undersells it — the migration to `chimera/*` (ADR-013) is the actual decision, not yet executed anywhere in code. |
| `hugginggpt/server/awesome_chat.py` | Retire on a schedule | **Still actively referenced** | More central than "retire on a schedule" implies: `run_jarvis.ps1` execs it as the *default* foreground process. Not peripheral legacy — it's what runs when the launcher is invoked normally. ADR-014's trial-period gate is still the right retirement mechanism, just needs this correction to how central the file is today. |
| `hugginggpt/server/bridge_server.py` | Keep short-term | **Still actively referenced** | Two launcher scripts spawn it directly; `device_integration.py` talks to it over HTTP as `awesome_chat.py`'s actual execution surface. Zero test coverage — flagged separately as a real gap (an unauthenticated, RCE-capable HTTP server with no tests). ADR-014's stated supersession trigger ("§6.5") doesn't literally exist in `CHIMERA_ECOSYSTEM_ARCHITECTURE.md`'s current section numbering — closest is invariant 5 of §6; citation fixed below. |
| `hugginggpt/server/jarvis/*` (skill/HAL framework) | Revive | **Safe to archive** (as-is, today) | Confirmed dead — zero references anywhere outside its own files. "Revive" is correctly a *future* Priority #3 task, not a present state; nothing depends on it today, so archiving it in place costs nothing and forecloses nothing. |
| `easytool/`, `taskbench/` | Remove or attribute | **Safe to remove** | Zero references in either repo, confirmed exhaustively. Unlike the other candidates, nothing unique is lost — these are unmodified copies of public upstream repos (Microsoft's EasyTool/TaskBench), re-cloneable if ever needed. Removal, not archival, is the cleaner outcome here specifically. |
| Brain `models/{reranker.py, router.py}`, `memory_module.py`, `logging_utils.py`, `tools/` | Delete | **Split — see ADR-014 amendment below** | Two of five paths don't exist in Brain at all. |

### ADR-014 amendment — path misattribution

`memory_module.py` and `logging_utils.py` **do not exist anywhere in the Brain repository.** Files with those exact names exist at `JARVIS/hugginggpt/server/memory_module.py` and `JARVIS/hugginggpt/server/logging_utils.py` — a different repo and directory than ADR-014's table states. Brain's own `PHASE3_TECH_DEBT_AUDIT.md` (which ADR-014 cites as its evidentiary basis) is explicit about this — it writes the full path `hugginggpt/server/memory_module.py` — but ADR-014's table dropped the `hugginggpt/server/` prefix when compiling the disposition list, misattributing two JARVIS-repo files to Brain. This is a drafting error in ADR-014 itself, caught by this dependency analysis, not a new decision — the disposition question for the *real* files (in JARVIS) was never actually made and needs a separate pass; it is not resolved by this ADR.

Of the three components that do exist in Brain:
- **`models/reranker.py`, `models/router.py`** — confirmed dead (zero references anywhere, no re-export used, no conflicting guidance in any Brain doc). **Safe to remove.**
- **`tools/`** — confirmed zero external references today, but Brain's own planning history disagrees with itself about its fate: `BRAIN_V2_DESIGN.md` (2026-06-12) says it "stays" and gains a manifest/risk-class extension (never implemented); `PHASE7`/`PHASE8` (2026-06-14, later and more specific) say retire. ADR-014 asserted "delete" without acknowledging this conflict. **Requires further investigation** — resolve which of Brain's own prior plans governs before acting, don't default to the newest one by assumption.

### Migration steps for each "Requires migration first" item

1. **Node SDK extraction**: fix the signing-order bug (`request_id` must be included before `sign_envelope()` runs, or the HMAC must cover the final payload) and de-duplicate `phone_executor.py`'s hand-copied verify logic *before* packaging `transport.py`/`signing.py`/`sandbox.py` as a standalone SDK — shipping the bug into a reusable package makes it every future node's problem instead of one file's.
2. **`brain_pc.py`**: either update `_smoke.py` to import from wherever the extracted node SDK lands, or explicitly retire `_smoke.py` alongside it with a replacement integration test — do not tag-and-freeze while the only passing test still imports it directly.
3. **`jarvis_prod` infra files**: the ADR-013 `chimera/*` rename is the actual migration; do it as one coordinated change across `protocol.py`, `brain_pc.py`, `agent_phone.py`, and `_smoke.py` together, not file-by-file, since they import each other.

### Corrections to earlier text

`bridge_server.py`'s ADR-014 entry cited "`CHIMERA_ECOSYSTEM_ARCHITECTURE.md` §6.5" as its supersession trigger — that document's §6 has five unnumbered invariants, not subsections; the intended reference is invariant 5 (defense in depth / independent root of trust). Noted here rather than silently editing the earlier ADR-014 table entry.
