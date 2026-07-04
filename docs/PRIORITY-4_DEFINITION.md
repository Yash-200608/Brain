# PRIORITY #4 — COGNITIVE DISPATCH & THE KEYSTONE DEMO

> **Status:** FROZEN — governing document for Priority #4, maintainer-approved
> 2026-07-04. Not an ADR (per ADR-012 the Decision Log stays decisions-only;
> this is a planning artifact, the same category as
> `CHIMERA_ECOSYSTEM_ARCHITECTURE.md`). **Produced by:** research pass across
> both repos (Brain + JARVIS), grounded in file-and-line citations throughout.
>
> **Freeze note (2026-07-04):** three maintainer refinements were applied
> before freezing — (1) the retirement trial's fixed "14-day / 95%" criteria
> were replaced with outcome-based criteria centered on sustained real-world
> use and demonstrated reliability (Section 3.6); (2) a **Non-negotiable
> Principles** section was added below; (3) every milestone was re-justified
> against the single question *"does this directly contribute to completing
> the Keystone Demo?"* — items that failed (the `authority_scope` field,
> pure dead-code hygiene) were deferred to Priority #5, and the ADR-014
> retirements were moved to the post-demo review milestone since they act on
> the demo's outcome rather than contribute to it (Section 5).
>
> Labeling convention, used consistently below:
> **[COMMITMENT]** = already decided/binding in existing ADRs or the
> ecosystem architecture — this document restates it, it does not create it.
> **[CONSTRAINT]** = a fact of the current implementation that shapes the work.
> **[RECOMMENDATION]** = this document's own proposal.

---

## 1. Executive Summary

**What Priority #4 is:** the priority in which Brain's cognition and the
Priority #3 execution spine finally meet. Priority #3 built the pipes — a
signed wire contract, a device registry, presence/state, and exactly one
dummy command ("ping") proven live end-to-end. Priority #4 makes the pipes
carry real intent: Brain plans a user's natural-language request, selects
real skills from live capability declarations, dispatches them as signed
commands with risk-tier gating and an approval flow, real device skills
execute behind an embodiment-side safety kernel, and the results flow back
into Brain's memory. Its centerpiece is the **Keystone Demo** (Section 3) —
referenced four times in `DECISION_LOG.md` (lines 37, 129, 145, 174) but
never defined until this document.

**Why it exists:** three separate ADR mechanisms are blocked on it.
ADR-011 requires "Priority #4's keystone demo must originate all planning
from Brain" (`DECISION_LOG.md:37`) [COMMITMENT]. ADR-014's entire review
trigger is "Priority #4's keystone demo reaches a defined trial-period
outcome" (`DECISION_LOG.md:129`) [COMMITMENT]. And the retirement of the
only daily-use production system (`awesome_chat.py`) is conditioned on that
demo having "run for a defined trial period and demonstrably replaced its
most-used daily commands" (`DECISION_LOG.md:145`) [COMMITMENT]. Until
Priority #4 happens, the legacy stack cannot be retired, `jarvis_core`'s
frozen-in-amber cognition cannot complete its ADR-014 lifecycle, and the
execution spine remains a proven-but-idle capability carrying one dummy
command.

**Why it is the natural successor to Priority #3:** the Priority #3
capstone specification explicitly fenced off "skill/task orchestration,
EventBus integration beyond what the spine requires, cognition refactoring,
jarvis_core retirement, advanced automation, or other Priority #4 work"
(`PRIORITY-3-EXECUTION-SPINE-CLOSURE.md:36-38`) [COMMITMENT]. That
exclusion list, read in reverse, is Priority #4's candidate scope. Every
deferred implementation decision from Priority #3 (the correlation field,
scope enforcement, the production node entrypoint, multi-node proof) was
deferred *to* this priority by name
(`PRIORITY-3-EXECUTION-SPINE-CLOSURE.md:224-248`).

**One-sentence definition:**

> Priority #4 delivers authenticated, risk-gated, Brain-planned skill
> dispatch over the Priority #3 execution spine, proves it by replacing the
> legacy stack's most-used daily commands through sustained real-world use
> (the Keystone Demo), and executes the ADR-014 legacy retirements that
> outcome unlocks.

---

## Non-negotiable Principles

These are the invariants Priority #4 inherits from ADR-011 through ADR-014,
`CHIMERA_ECOSYSTEM_ARCHITECTURE.md`, and the Priority #3 execution spine.
They are not up for re-decision inside this priority. Any milestone, design
choice, or shortcut that would violate one of these is out of scope by
definition — if a genuine need to break one arises, work stops and goes to
the maintainer as a new ADR, never resolved silently in code (per the
Priority #3 no-new-ADRs-in-implementation precedent). Each cites the source
that binds it.

**NP-1 — Brain is the sole cognitive authority; JARVIS only embodies.**
All planning, memory, orchestration, goal state, and authorization *policy*
live in Brain. No node or embodiment surface may originate a multi-step
plan, form cross-session memory, or make any decision whose shape Brain has
not pre-authorized. The keystone demo's plans originate in Brain, nowhere
else. *(ADR-011; `CHIMERA_ECOSYSTEM_ARCHITECTURE.md` §1 line 18, §4 line 50.)*

**NP-2 — The cognition/embodiment boundary is functional and absolute:
never both.** A component is a cognition authority or an embodiment
participant, never both. On-device inference is fine as long as its outputs
are limited to capability/state declarations and execution of
Brain-authorized action shapes. This is what makes the rule enforceable by
inspection rather than intuition. *(`CHIMERA_ECOSYSTEM_ARCHITECTURE.md` §1
line 18, line 22.)*

**NP-3 — Fail-closed is the default, everywhere.** Any request whose
identity, signature, or authorization cannot be positively verified is
rejected — never defaulted to a privileged, anonymous, or "trusted-for-now"
identity. Unknown/future risk-tier values resolve to maximum restriction,
never permissiveness. Verification failure is rejection, not a trust tier.
*(`CHIMERA_ECOSYSTEM_ARCHITECTURE.md` §6 invariant 1; `RiskTier` fail-closed
design, `protocols/chimera_contract.py`.)*

**NP-4 — Every boundary message is a signed, versioned envelope; unsigned
or unverifiable messages are rejected at the boundary.** The HMAC-with-
nonce-and-skew-window contract (`ChimeraEnvelope`) is the only thing that
crosses Brain↔node. Extending it obeys the versioning rules: a new optional
field is additive within a major, a new required field forces a major bump,
and both sides of the vendored contract move in lockstep. *(ADR-013;
`CHIMERA_ECOSYSTEM_ARCHITECTURE.md` §5 line 54, §8 line 81.)*

**NP-5 — Capability declaration, never hardcoded skill lists.** Brain builds
its plan of available actions from live declarations advertised by nodes,
never from a static table baked into Brain's code. A conformant new node is
automatically plannable with no Brain-side code change, and Brain's
authority logic special-cases no particular embodiment platform. *(ADR-014
skill/HAL-catalog revival; `CHIMERA_ECOSYSTEM_ARCHITECTURE.md` §5 line 55,
§9 lines 89–90.)*

**NP-6 — Authorization-relevant fields are authority-assigned, not
client-supplied.** Scope, role, and risk-ceiling values come exclusively
from Brain's policy layer (or, for a node's own declared ceiling, from
whoever operates that node) and are structurally rejected if present in
inbound payloads from the untrusted side — never merged, defaulted, or
coalesced from caller input. *(`CHIMERA_ECOSYSTEM_ARCHITECTURE.md` §6
invariant 4.)*

**NP-7 — Risk-gated approval precedes any execution or safety-rewrite, and
approvals are distinct-principal and single-use.** A destructive or
risk-gated action's approval must (1) originate from a principal distinct
from and privileged above the requester, (2) be verified against the
already-computed risk tier *before* any execution or rewrite step runs, and
(3) be single-use and bound to that specific action instance, never
replayable. Risk classification always precedes and gates any rewrite,
never the reverse. *(`CHIMERA_ECOSYSTEM_ARCHITECTURE.md` §5 line 57; the
Priority #1 `core/executor.py` ordering fix embodies the same rule.)*

**NP-8 — Defense in depth with an independent root of trust.** Brain's
authorization is necessary but never sufficient: every embodiment platform
enforces its own safety kernel on every dispatched action. For the highest
risk tier(s), that kernel's ceilings and irreversible-action gates are
operator-configured at the node and are not modifiable by any
Brain-originated message, signed or not, and require a confirmation channel
Brain cannot itself satisfy. A compromised-but-correctly-signed Brain must
not be able to defeat the node's kernel. *(`CHIMERA_ECOSYSTEM_ARCHITECTURE.md`
§6 invariant 5; ADR-014 `bridge_server.py` supersession trigger.)*

**NP-9 — Brain and JARVIS stay separate services across the boundary; no
component may assume co-location.** They are independently deployable, in
independent repos, and no code imports across the boundary. No component
may assume single-machine (T0) deployment. *(ADR-011;
`CHIMERA_ECOSYSTEM_ARCHITECTURE.md` §2, §7 line 75; CLAUDE.md "keep Brain
and Jarvis as separate services".)*

**NP-10 — Retire, don't delete; and never retire before the objective gate
is met.** Superseded components with production history are git-tagged and
left in place or archived, not deleted. The legacy stack is not shut off
until the keystone demo's outcome-based trial objectively says so; a failed
trial defers retirement with evidence, never silently continues or forces
it. *(ADR-014 disposition table and general policy; C2/C3.)*

**NP-11 — Observed working, not merely built.** Every milestone leaves the
system runnable, verified by the full test suite (zero regressions), with
load-bearing claims verified against real behavior — the discipline that
caught six real bugs across Priority #3. "Designed and built" is not "done";
the demo's success criteria are demonstrations, not assertions. *(Priority
#3 closure; the project's documented historical failure mode of stopping at
"built".)*

---

## 2. Research Findings

Everything below was verified by direct file reads this session, not
memory. One briefed source could not be verified because **it does not
exist**: no file named `SECURITY_BASELINE_V2.md` exists anywhere in either
repository (glob across both repos, 2026-07-04). The nearest equivalents
are `JARVIS/docs/architecture/SECURITY_MODEL.md` and Brain's Priority #1
closure work. **[RECOMMENDATION]** Treat those as the security baseline;
if a consolidated baseline document is wanted, producing it belongs in
Priority #4's documentation-closure milestone, not silently substituting.

### 2a. Binding architectural commitments

| # | Commitment | Source |
|---|---|---|
| C1 | The keystone demo "must originate all planning from Brain"; JARVIS "never originates multi-step plans" | `DECISION_LOG.md:37`, `:23` (ADR-011) |
| C2 | `awesome_chat.py` stays in production until the keystone demo "has run for a defined trial period and demonstrably replaced its most-used daily commands" | `DECISION_LOG.md:145` (ADR-014) |
| C3 | ADR-014's review trigger: "Priority #4's keystone demo reaches a defined trial-period outcome"; retirement timelines revisited "once Priority #4's keystone demo has an actual trial-period outcome (success/failure data), not speculatively" | `DECISION_LOG.md:129`, `:174` |
| C4 | `bridge_server.py` is "superseded once JARVIS root `core/`'s safety kernel is wired per `CHIMERA_ECOSYSTEM_ARCHITECTURE.md` §6 invariant 5" | `DECISION_LOG.md:146` |
| C5 | `jarvis_core` cognition: git-tag `jarvis_core-v1-cognition`, stop maintaining, do not delete; "extraction first, freeze after" — extraction completed in Priority #3 M1, freeze is "explicitly Priority #4+ work" | `DECISION_LOG.md:141`, `:168`; closure `:112-115` |
| C6 | `hugginggpt/server/jarvis/*` is to be "revive[d] as the skill/HAL catalog" — "the only real dynamic-capability-discovery mechanism found anywhere; currently dead, becomes load-bearing under the new spine" | `DECISION_LOG.md:147` |
| C7 | The adopted ADR-013 message shape includes "correlation-id-based request/response matching"; Priority #3's omission of the field is on record as "implementation detail in service of ADR-013/014, not a new architectural decision" — so adding it **completes an accepted decision, no new ADR needed** | `DECISION_LOG.md:99`, `:198-202` |
| C8 | Envelope requirements: "sender identity, authority-scope ..., message type, schema version, correlation id, timestamp, and a signature over all of the above" | `CHIMERA_ECOSYSTEM_ARCHITECTURE.md:54` (§5) |
| C9 | "Capability declaration, not hardcoded skill lists. ... Brain builds its plan of available actions from live declarations, never a static table baked into Brain's code" | `CHIMERA_ECOSYSTEM_ARCHITECTURE.md:55` |
| C10 | Approval flow, three mandatory properties: (1) approver is a distinct, more-privileged principal than the requester; (2) approval verified against the already-computed risk tier *before* any execution or safety-rewrite; (3) single-use, bound to the specific action instance | `CHIMERA_ECOSYSTEM_ARCHITECTURE.md:57` |
| C11 | Invariant 5: "Every embodiment platform enforces its own safety kernel on every dispatched action — and for the highest risk tier(s), that kernel's ceilings and irreversible-action gates are operator-configured at the embodiment platform and are not modifiable by any Brain-originated message, signed or not. The highest tier(s) require a confirmation channel Brain cannot itself satisfy" | `CHIMERA_ECOSYSTEM_ARCHITECTURE.md:67` |
| C12 | Skills stay embodiment-side only while "outputs are limited to capability/state declarations and execution of Brain-authorized action shapes"; both local-autonomy forms "exclude: multi-step planning, memory formation beyond the local action log, and any decision Brain hasn't pre-authorized the shape of" | `CHIMERA_ECOSYSTEM_ARCHITECTURE.md:18`, `:50` |
| C13 | A new *optional* envelope field is additive within a major version; a new *required* field is a major-version bump | `CHIMERA_ECOSYSTEM_ARCHITECTURE.md:81` (§8) |
| C14 | A conformant new node is "automatically plannable — no Brain-side code change required"; Brain "must not special-case 'the JARVIS client' anywhere in its authority logic" | `CHIMERA_ECOSYSTEM_ARCHITECTURE.md:89-90` (§9) |
| C15 | "No component may assume T0" (single-machine deployment) | `CHIMERA_ECOSYSTEM_ARCHITECTURE.md:75` (§7) |
| C16 | A concrete versioned schema + conformance test suite is "the actual compliance artifact" and must exist "at a stable, referenced location once written" — this pointer is still unresolved | `CHIMERA_ECOSYSTEM_ARCHITECTURE.md:58` |

### 2b. Existing implementation constraints

| # | Constraint | Source |
|---|---|---|
| I1 | `has_scope()` exists but is called by zero routes; scope enforcement deliberately deferred at Milestones 9 and 12 to be done "in one coherent pass"; named "Priority #4's first order of business" | closure `:171-177`, `:260-263`; `Brain/api/routes/devices.py` TODO(auth) |
| I2 | `ChimeraEnvelope` has no correlation/request_id field (`extra="forbid"` — see risk R4); `send_command_and_await_response()` matches on `(verb, action)`, unsafe for concurrent commands | closure `:178-185`; `Brain/protocols/chimera_contract.py:83-110` |
| I3 | Repeated `send_command_and_await_response()` calls accumulate response-topic handlers | closure `:186-191` |
| I4 | No always-on JARVIS node entrypoint; `run_chimera_demo_node.py` is a demo script (CLI-flag key/identity) | closure `:202-207` |
| I5 | Spine proven single-node only; never two concurrent nodes, never a mid-session reconnect | closure `:208-213` |
| I6 | `agent_phone.py` implements 10 real `phone.*` skills (battery, tts, sms.send, torch, vibrate, notify, ring, location, app.open, whatsapp.send) — working Termux code | `jarvis_prod/agent_phone.py:282-292` |
| I7 | No `pc.*` skill executor exists anywhere despite `brain_pc.py:196-204` advertising 14 of them; root `core/` safety kernel's `_dispatch` is a stub (readiness blocker 3, no resolution evidence) | `JARVIS/docs/context/CURRENT_STATUS.md`; readiness review `:28` |
| I8 | `brain_pc.py:196-204` holds a hardcoded `_known_skills` set — exactly the "static table" pattern C9 forbids carrying forward | `jarvis_prod/brain_pc.py:196-204` |
| I9 | The dead `jarvis/schema.py` already models `Command` (skill+params+id+ttl, id-correlated), `Response`, `Event`, retained `State`, planning `Request`, and a per-node catalog topic — but on the retired `jarvis/node/` namespace | `hugginggpt/server/jarvis/schema.py:29-169` |
| I10 | The legacy daily-use surface is `awesome_chat.py`'s `parse_device_command`: ~24 phone actions + ~35 computer actions, LLM-parsed from natural language, destructive actions behind the Priority #1 confirmation gate | `hugginggpt/server/awesome_chat.py:462-621` |
| I11 | Brain's cognition seam: `JarvisOrchestrator.handle()` → `CognitivePipeline`; a real in-process `EventBus` exists (`events/bus.py:28-53`); `Task.risk` is an int (`core/task.py:27`) with `RiskTier.from_legacy_int()` as the declared boundary helper | `Brain/orchestrator/orchestrator.py:42-88`; `Brain/protocols/chimera_contract.py:62-79` |
| I12 | The local Mosquitto broker accepts anonymous connections; MQTT ACLs are flat; no MQTT TLS (Tailscale is the encryption layer) | P3 closure; `JARVIS/docs/roadmap/MASTER_ROADMAP.md:111`, `:115` |
| I13 | Both readiness-review Critical blockers are resolved; High blockers 3 (`_dispatch` stub), 4 (`tools/` fate), 5 (scope enforcement), 6 (API-key provisioning docs) and can-wait item 11 (`bridge_server.py` test coverage) remain open | audits research, readiness review `:27-38` |

### 2c. Historical notes (context, not constraints)

- `JARVIS/docs/roadmap/MASTER_ROADMAP.md` (2026-07-01) predates ADR-011.
  Its Phases 1–3 (decide canonical Brain in-repo, prove `jarvis_core` runs,
  merge islands) were **superseded by ADR-011** — the Brain repo won and
  `jarvis_core` cognition is retired unvalidated. Its Phase 4 (first live
  Tailscale deployment), Phase 5 (retire losing islands), and parts of
  Phase 6 map onto Priority #4/#5 content. Its §6.5 wording ("running ...
  for a defined trial period and has demonstrably replaced at least the
  legacy stack's most common daily commands") is the recognizable ancestor
  of ADR-014's trial-period gate.
- The word "keystone" appears nowhere in the JARVIS docs tree (grep,
  2026-07-04) — the concept exists only in Brain's `DECISION_LOG.md` and
  the Priority #3 closure. This document is its first definition.
- `CHIMERA_ECOSYSTEM_ARCHITECTURE.md:22` says "four independent
  implementations" but enumerates three — a textual mismatch in the
  source, noted here, not corrected silently.
- ADR-013/ADR-014 originally assigned the skill-catalog revival to
  **Priority #3** (`DECISION_LOG.md:116`, `:168`), but the user-authored
  capstone spec excluded "skill/task orchestration" from Priority #3, and
  the closure confirms it was not done. The work sits unclaimed on paper.
  **This document explicitly claims it for Priority #4** — flagged as a
  documented scope transfer, not a silent redefinition.

### 2d. Suggestions on record that are NOT commitments

From `PRIORITY-3-EXECUTION-SPINE-CLOSURE.md:224-248` ("Recommendations
for Priority #4" — advisory, authored at Priority #3 closure):
scope enforcement first; correlation-ID alongside skill/task dispatch; a
real always-on node entrypoint; multi-node proof before designs that
assume it; continuation of the small-milestone discipline. This document
adopts all five as **[RECOMMENDATION]**s and folds them into Sections 4–5;
their adoption becomes binding only with maintainer sign-off on this
document.

---

## 3. The Keystone Demo

Everything in this section is **[RECOMMENDATION]** except where a
[COMMITMENT] tag marks an element as pre-bound by C1–C3. The demo is
deliberately shaped so that completing it forces every architectural
property Priority #4 must prove — planning from Brain (C1), live
capability declarations (C9), risk-gated approval (C10), an
embodiment-side kernel (C11), correlated dispatch (C7/C8), and genuine
replacement of daily-use commands (C2).

### 3.1 User story

> As the owner, I type a natural-language request into the Brain dashboard
> — "what's my phone's battery?", "send Mom a WhatsApp that I'm running
> late", "open Spotify on my phone", "lock the PC" — and the request is
> planned by Brain, executed on the right real device over the signed
> spine, and answered back to me in the dashboard with a truthful outcome,
> without the legacy ADB stack being involved at any step. Requests that
> are risky (delete, shutdown, arbitrary shell) stop and ask me first,
> through a gate the phone/PC enforces even if Brain itself were
> compromised.

Voice input, camera/vision, and multi-device scene automation ("I'm headed
to bed") are explicitly **not** part of the demo (Section 9) — the demo is
the narrowest realistic slice that satisfies C1–C3.

### 3.2 Start condition

- Brain API + dashboard running on the PC (existing `brain-api` /
  `brain-dashboard` processes), MQTT enabled with a real HMAC key.
- At least **two** live JARVIS nodes connected to the broker via the
  production node entrypoint (not the demo script): the PC node and the
  Nothing Phone 3a Lite node (Termux, over Tailscale) — two nodes because
  I5 requires multi-node proof and C2's daily commands are mostly phone
  actions.
- Each node has **declared its skill capabilities** over the spine (C9);
  Brain's device registry holds those declarations; no hardcoded skill
  table exists on the Brain side (retiring the I8 pattern).
- The legacy stack (`awesome_chat.py` + `bridge_server.py`) is still
  running and untouched — per C2 it is not shut off until the trial
  outcome says so.

### 3.3 End condition

- The demo request set (3.6) has each round-tripped successfully at least
  once, live, observed in the dashboard.
- The **trial** then runs: the owner uses Brain (not the legacy stack)
  for the confirmed daily-command list until the outcome-based evidence in
  3.6(2) exists — sustained adoption, demonstrated reliability, real
  conditions — with no fixed calendar endpoint.
- At trial end, an evidence-based outcome report exists (success/failure
  per 3.6/3.7), which is exactly the "defined trial-period outcome"
  ADR-014's review trigger needs (C3). The ADR-014 retirement review then
  happens as its own step (Section 6) — the demo *produces* the outcome;
  it does not itself retire anything.

### 3.4 Participating systems

| System | Role in the demo |
|---|---|
| Brain dashboard (`frontend/dashboard/`) | Input surface + result display + approval UI |
| Brain API (`api/`) | Auth (with scope enforcement — I1 resolved), query intake, approval endpoint |
| Brain cognition (`orchestrator/` → `core/pipeline.py`, `agents/planner.py`) | Parses intent, produces the plan — ALL planning here (C1) |
| Brain dispatch bridge (new, thin) | Plan step → risk tier (`RiskTier.from_legacy_int` boundary, I11) → approval gate (C10) → `send_command_and_await_response()` with correlation id (C7) |
| MQTT broker (local Mosquitto, Tailscale-bound for the phone) | Transport |
| `jarvis_node_sdk` (both nodes) | Signed envelope verify, skill registry + capability declaration publisher, safety-kernel hook (C11), skill execution |
| Phone node (Termux) | Executes the migrated `phone.*` skills (I6) |
| PC node | Executes a minimal `pc.*` skill set on top of the root `core/` safety kernel (resolves I7 for the demo's subset) |
| Brain memory/goals | Records dispatched commands and outcomes (audit trail; C12's "reconciled, not silent" spirit) |

### 3.5 Expected runtime flow (single request, e.g. "send Mom a WhatsApp that I'm running late")

1. Owner submits text in the dashboard → `POST /api/query` (authenticated,
   scope-checked).
2. Brain cognition classifies the request as requiring a device action and
   plans it: one step, skill `phone.whatsapp.send`, params inferred —
   selected **from the live capability declarations in the device
   registry**, never a static list (C9). Planning happens nowhere else (C1).
3. The dispatch bridge computes the risk tier for the step. Medium/low →
   proceed; high (delete/shutdown/shell) → emit an approval request and
   stop until the approval flow (C10) completes; approvals are single-use
   and instance-bound.
4. Brain signs and publishes a `ChimeraEnvelope` `cmd` (with `request_id`
   correlation, C7/C8) to `chimera/phone-node/cmd`.
5. The phone node verifies the signature, runs its **local safety kernel
   check** on the action (C11 — independent of Brain's authorization),
   executes the real Termux skill, and publishes a signed, correlated
   `response`.
6. Brain verifies the response, resolves it to the in-flight request,
   records the outcome in memory, and the dashboard shows the result.
7. Every step is visible in an audit trail (who asked, what was planned,
   what tier, who approved, what the node answered).

### 3.6 Success criteria (measurable)

The demo *passes* when all of the following hold:

1. **Command set coverage:** each command class in the confirmed
   most-used list round-trips live at least once via the flow in 3.5.
   **[RECOMMENDATION — needs owner confirmation, Open Question Q1]**
   Proposed list, derived from the intersection of the legacy surface
   (I10) and the working phone skills (I6), plus the two PC actions the
   owner uses daily per the docs: `phone.battery`, `phone.whatsapp.send`,
   `phone.sms.send`, `phone.app.open`, `phone.notify` (or `.tts`),
   `pc.system.lock`, `pc.volume.set`/`pc.media.control`.
2. **Sustained real-world adoption and demonstrated reliability
   (outcome-based — no fixed calendar length, no arbitrary percentage
   bar):** the trial is complete only when ALL of the following are
   evidenced by instrumentation, not asserted:
   (a) **Adoption** — for every covered command class, Brain is the path
   the owner actually uses day-to-day: zero invocations of the legacy
   stack for those classes across the entire trial window, proven by
   legacy-side invocation logging (absence measured, not remembered);
   (b) **Reliability** — every failure that occurred during the trial was
   root-caused and fixed, and no failure class recurred after its fix; at
   review time, no covered command class has an unresolved or unexplained
   failure;
   (c) **Real conditions** — the trial window includes the conditions
   that break naive implementations: multiple phone sleep/wake (Doze)
   cycles, at least one broker or node restart/reconnect mid-trial, and
   multi-day continuous node uptime — so reliability claims rest on lived
   use rather than staged sessions.
   The ADR-014 review judges this evidence and the maintainer closes the
   trial — not a timer.
3. **Planning locus:** zero plans originate outside Brain — verified by
   the audit trail plus the absence of any planning code path on the node
   (C1, C12).
4. **Live declarations:** deleting a skill from a node's declaration
   removes it from Brain's plannable set without any Brain code change
   (C9, C14) — demonstrated once during the demo.
5. **Approval gate:** at least one high-tier command (e.g. `pc.shell.run`)
   is demonstrated to (a) block without approval, (b) execute exactly once
   with a single-use approval, (c) reject replay of the same approval
   (C10).
6. **Kernel independence:** at least one command that Brain authorizes is
   demonstrated to be **refused by the node's local kernel** when the
   operator-configured ceiling forbids it (C11) — proving the last line of
   defense works.
7. **Concurrency:** two commands in flight to the same node at once
   resolve to their own callers correctly (correlation id, C7; resolves
   I2/I3).
8. **Both suites green** at every milestone and at trial end; zero
   regressions (standing Priority #3 discipline).

### 3.7 Failure criteria (any one fails the demo)

- Any plan or skill selection originating on a node (C12 violation).
- A high-tier action executing without a distinct-principal, single-use,
  tier-checked-first approval (C10 violation).
- The node kernel accepting a ceiling change delivered via any
  Brain-originated message (C11 violation).
- The owner reverting to the legacy stack for any covered command class
  during the trial, a previously-fixed failure class recurring, or the
  trial being closed without the 3.6(2) evidence actually existing. (An
  honestly-failed trial — evidence showing the spine isn't ready for
  daily reliance — is a *valid outcome* per C3: ADR-014's review then
  defers retirement with data, not speculation.)
- Unsigned/tampered/replayed envelopes being accepted anywhere.

---

## 4. Architectural Goals

### Priority #4 MUST accomplish

1. **Scope enforcement across all Brain routes in one coherent pass** —
   first order of business, before any new device-level action ships
   (I1; closure recommendation 1).
2. **Complete the ADR-013 envelope shape**: add optional `request_id`
   (correlation) — and, found by this research, the §5-required
   `authority_scope` field is also absent from `ChimeraEnvelope` (C8).
   Both are optional fields (additive, C13), rolled out coordinated
   across both repos via the existing vendoring sync (see risk R4).
3. **Skill capability declaration** (C9): nodes declare skills over the
   spine; Brain's registry stores them; planning consumes only live
   declarations. Salvage the dead `jarvis/schema.py` catalog concepts
   (I9) under the `chimera/*` grammar — this executes the C6 revival, as
   the explicitly-claimed scope transfer noted in 2c.
4. **Real skill execution on nodes**: migrate the 10 working `phone.*`
   Termux skills (I6) onto `jarvis_node_sdk`'s command dispatch; build
   the minimal `pc.*` subset the demo needs on top of root `core/`'s
   safety kernel, giving `_dispatch` its first real handlers (I7).
5. **The Brain planning→dispatch bridge** (C1): a plan step that names a
   declared skill, risk-tiered via the existing int→`RiskTier` boundary
   (I11), dispatched via `send_command_and_await_response`.
6. **The approval flow** with C10's three properties, plus the
   embodiment-side safety kernel hook on every dispatched action with
   operator-configured ceilings (C11).
7. **A production node entrypoint** (config-sourced HMAC key + node
   identity, auto-start capable) on PC and phone (I4), retiring
   the demo script from any production role.
8. **Multi-node live operation** (PC + phone concurrently, I5).
9. **The Keystone Demo + trial period + outcome report** (Section 3).
10. **The ADR-014 executions that are already unblocked or become
    unblocked** (Section 6), including the `jarvis_core` cognition
    tag-and-freeze (C5).
11. **A minimal contract conformance suite** at a stable referenced
    location, resolving C16's dangling pointer for the parts of §5 the
    spine now implements. [RECOMMENDATION — scope it minimally: the
    envelope + capability-declaration schema tests, not a full
    certification harness.]

### Priority #4 must NOT attempt

(Section 9 has the full exclusion list with rationale.) Headlines: no
voice interface; no vision/camera nodes; no new hardware nodes beyond the
two named; no T2 federation/handoff; no EventBus↔MQTT generalization
beyond what dispatch needs; no Brain cognition refactoring beyond the
dispatch seam; no scene/multi-step automation routines; no
`hugginggpt/web` rebuild; no MQTT TLS/per-node-ACL hardening (P5, unless
the trial exposes an acute need); no retirement executed before its gate
is objectively met.

---

## 5. Milestone Proposal

Sized to match late Priority #3 milestones (one seam, independently
verifiable, full-suite green after each). Numbering is priority-local
(P4-M1…). Sequencing rationale: security first (I1), then contract, then
capability, then execution, then the dispatch bridge, then ops, then the
demo, then the outcome-driven review.

**Every milestone below passed the freeze test — "does this directly
contribute to completing the Keystone Demo?"** — recorded in the *Serves
the demo by* column. Items that failed the test were removed from the plan
and listed under "Deferred to Priority #5" after the table. The single
apparent exception, M12, does not *contribute to* the demo — it *acts on
the demo's outcome* (the ADR-014 retirements whose sole trigger is the
demo result, C2/C3); it is retained because executing those retirements is
Priority #4's defining charter per ADR-014, and it runs only after the
demo has produced its outcome.

| # | Objective | Serves the demo by | Expected code changes | Verification | Done when |
|---|---|---|---|---|---|
| M1 | Scope enforcement in one coherent pass | The demo adds consequential new endpoints (skill-invoke, approve); NP-3/NP-6 and success criteria 5 require them scope-safe — shipping them onto the unenforced model would repeat the `/ping` deferral at higher stakes | `has_scope()` wired into every protected route (query, memory, goals, sessions, devices incl. `/ping` and the new P4 endpoints); scope taxonomy documented; remove `TODO(auth)` markers | Route tests: correct scope → 200, missing → 403; all existing tests green | Zero routes without a scope check; suite green |
| M2 | Correlation ID (ADR-013 remainder) | Success criterion 7 (concurrent dispatch) is impossible without it; the demo issues real overlapping skill traffic | `chimera_contract.py`: optional `request_id`; sync script re-run; `send_command_and_await_response` correlates on `request_id`, falls back to `(verb,action)`; response-handler cleanup fixes I3 | Contract round-trip tests both repos; concurrent-commands test (two in flight, same node+action, distinct results); tamper tests | Correlated concurrent dispatch proven via fake broker; both suites green |
| M3 | Capability declaration (node side) | Success criterion 4 and NP-5: the demo plans from live declarations, which nodes must first publish | `jarvis_node_sdk`: skill registry + `publish_capabilities()` (signed, on connect + on change), salvaging `jarvis/schema.py`'s catalog shape under `chimera/<node>/capabilities` | Fake-broker tests: declaration publishes, is signed, verifies | A node can declare a skill list over the spine |
| M4 | Capability registry (Brain side) | The demo's planner selects skills *from the registry* (NP-1/NP-5); without Brain-side storage there is nothing to plan against | `chimera/+/capabilities` subscriber → DeviceStore stores declared skills; devices API exposes them; dashboard lists them | Route + subscriber tests mirroring the P3 M5/M7 pattern | Declared skills visible in `GET /api/devices` |
| M5 | Real phone skills on the SDK | The demo executes real `phone.*` skills, not the dummy ping | Port `agent_phone.py`'s 10 skill impls into the node SDK dispatch (replacing dummy-only ping); keep ping | Unit tests with faked Termux boundary; live one-skill spot check | `phone.battery` (at minimum) executes for real via the spine |
| M6 | PC skill subset + safety kernel wiring | The demo covers `pc.system.lock`/volume and success criterion 6 (a node-kernel refusal) requires the kernel on the PC action path | Minimal `pc.*` set (lock, volume/media, shell-run gated) executing through root `core/` safety kernel (first real `_dispatch` handlers, NP-8); operator-config ceiling file | Kernel-refusal test (C11), risk-tier tests, live spot check | A Brain-authorized command demonstrably refused by local ceiling |
| M7 | Brain dispatch bridge + approval flow | This IS the demo's core path: NL → Brain plan (NP-1) → risk tier → approval (NP-7) → signed dispatch; success criteria 3 & 5 | Plan-step→skill mapping from live declarations only; risk tier via `from_legacy_int`; approval endpoint + single-use instance-bound approval store (NP-7); audit-trail records | Tests for all three NP-7 properties; blocked-without-approval test; audit-trail assertions | One NL request → planned → gated → dispatched → recorded, via fake broker |
| M8 | Production node entrypoint | The trial (success criterion 2) cannot run on a CLI-flag demo script; needs an unattended, config-sourced node | Config-sourced (env/file) HMAC + node identity; graceful shutdown; auto-restart guidance; PC first | Runs live locally as a service; demo script marked dev-only | PC node runs unattended ≥24h with heartbeats unbroken |
| M9 | Phone node deployment (ops) | The demo's command list is mostly phone actions; the phone node must be live on real hardware over Tailscale | Termux install of the SDK node; Tailscale broker binding; API-key/HMAC provisioning documented (closes readiness blocker 6) | Live: phone declares capabilities, answers `phone.battery` over Tailscale | Phone node live from real hardware |
| M10 | Multi-node + dashboard command console | Success criterion 7 needs two concurrent nodes; the demo's input/approval/audit surface is the dashboard | Both nodes concurrent; dashboard: per-skill invoke + approval UI + audit view | Live concurrent dispatch to both nodes; UI walkthrough | I5 closed; owner can drive the demo entirely from the dashboard |
| M11 | Keystone Demo + trial start | It IS the demo (3.6 items 1, 3–7) and starts the outcome-based trial | Demo checklist executed; trial instrumentation (command log/counters, legacy-side invocation logging) | Each demo criterion demonstrated live and recorded | Trial running with measurement in place |
| M12 | Trial outcome + ADR-014 retirements + docs closure | *Acts on* the demo outcome (not a contributor): executes the retirements ADR-014 gates on the trial result — P4's defining charter | Outcome report; ADR-014 review executed against Section 6 gates; on success: tag `jarvis_core-v1-cognition`, remove the four deprecated shims, retire `brain_pc.py`/`bridge_server.py`/`awesome_chat.py` per their gates; `PRIORITY-4-CLOSURE.md`; roadmap/status docs updated | Outcome report cites measured evidence; each retirement gate objectively evaluated (executed if met, deferred-with-evidence if not) | Priority #4 Definition of Done (Section 10) fully checked |

The trial's elapsed real-world time (M11→M12) is lived-use measurement, not
idle waiting — its length is set by when the outcome-based evidence in
3.6(2) actually exists, not by a timer.

### Deferred to Priority #5 (failed the "serves the demo" test)

These were in an earlier draft of this plan and are cut from Priority #4
because they neither contribute to completing the Keystone Demo nor are
gated on its outcome:

- **`authority_scope` envelope field** — a genuine §5-completeness gap
  (Appendix A #6), but the demo never exercises it and nothing in the demo
  path depends on it. Its natural home is T2/federation work (§7), where
  authority-scope actually matters. Deferring it now is recorded here so it
  is not silently dropped.
- **Pure dead-code hygiene** — deleting Brain `models/{reranker,router}.py`
  and removing the vendored `easytool/`/`taskbench/` benchmarks. Already
  "can wait" per the Priority #3 closure; their only P4 justification was
  "cheap, and P4 is the named owner," which fails the freeze test. (The
  `jarvis_core` shim removal, by contrast, stays in P4 — it is part of
  completing the `jarvis_core` freeze, which M12 executes as an
  ADR-014 retirement.)
- Everything already listed as P5+ in Section 7.

---

## 6. Legacy Retirement Plan (ADR-014 execution)

Objective exit criteria per component. **The gates are commitments (C2–C5);
the specific thresholds are [RECOMMENDATION]s pending Q1/Q2 sign-off.**

| Component | Can be executed when | Exit criteria (objective) |
|---|---|---|
| `jarvis_core` cognition freeze (C5) | At M12 (after the trial outcome) — precondition ("extraction first") met in P3-M1, `_smoke.py` decoupled, so it is technically executable earlier, but it is grouped with the other retirements at the ADR-014 review since none of them serve the demo | Tag `jarvis_core-v1-cognition` pushed; no repo imports the frozen modules (grep-proven); the four deprecated shims removed |
| `brain_pc.py` retire (same tag policy) | After M7 (Brain-side planning replaces its embedded orchestration role) and M9 (its phone counterpart replaced); executed at M12 | Tagged; `run_jarvis.ps1` prod path no longer execs it; `_smoke.py` already decoupled (P3-M1); replacement integration test = the spine's own live-path tests |
| `jarvis_prod` infra (`protocol.py`, `jobs.py`, `telegram_gateway.py`, `scheduler.py`) | Not retired in P4 — ADR-014 says keep/migrate; rename already done (P3-M1) | Out of P4 scope beyond what M5/M9 physically reuse; Telegram/scheduler migration is P5+ |
| `bridge_server.py` retire (C4) | After M6 (root `core/` kernel wired = the stated supersession trigger) **and** trial evidence | Kernel wired per invariant 5; the full trial window shows zero `bridge_server` invocations for the covered `pc.*`/`computer` classes (its endpoints logged to prove non-use, per the outcome-based criteria in 3.6(2)); then stop launching it, tag, keep in place |
| `awesome_chat.py` retire (C2/C3) | Only at ADR-014 review (M12) with a **successful** trial outcome | Trial passed per 3.6 — coverage of the confirmed command list plus the outcome-based sustained-adoption / demonstrated-reliability / real-conditions evidence; ADR-014 review records the outcome and the retire decision; then stop launching as default foreground process (`run_jarvis.ps1`), tag, keep in place. A failed trial = documented deferral with evidence, not silent continuation |
| Demo node → production node | M8 (PC) / M9 (phone) | `run_chimera_demo_node.py` demoted to dev-tool with a docstring saying so; production entrypoint is the only thing ops docs reference |
| `hugginggpt/server/jarvis/*` archive | After M3/M4 salvage the catalog concepts | Concepts ported and tested under `chimera/*`; package git-tagged and archived per ADR-014 general policy |
| JARVIS `memory_module.py` / `logging_utils.py` | Disposition **was never decided** (ADR-014 amendment) | P4-M12 makes and records the decision (a one-line JARVIS-log entry — JARVIS-internal per ADR-012); not silently bundled here |
| Brain `tools/` | Blocked on resolving the `BRAIN_V2_DESIGN.md` "stays" vs PHASE7/8 "retire" conflict (readiness blocker 4) | **[RECOMMENDATION]** resolve during M6/M7 design only if the dispatch bridge would touch `tools/`; otherwise defer the resolution explicitly to P5 — never default silently to either document |

---

## 7. Technical Debt Review (all open items from Priority #3 and earlier)

**Required before Priority #4 feature work (i.e., it IS the first milestone):**

1. Scope enforcement (closure item 1 / readiness blocker 5) — every new
   P4 endpoint (approval, capabilities, skill invoke) would otherwise ship
   into the same unenforced model; flagged three times; doing it after
   would mean a fourth deferral. → M1.

**Required during Priority #4 (each is load-bearing for a specific milestone
that serves the demo):**

2. Correlation/`request_id` (closure item 2) — concurrent dispatch is
   inherent to real skill traffic; the accepted ADR-013 shape already
   includes it. → M2.
3. Response-handler accumulation (closure item 3) — same seam as M2; fix
   together.
4. Production node entrypoint (closure item 5) — the trial cannot run on
   a CLI-flag demo script. → M8.
5. Multi-node proof (closure item 6) — the demo requires two nodes. → M10.
6. Root `core/` `_dispatch` stub (readiness blocker 3) — the PC skill
   subset is precisely its first real implementation. → M6.
7. API-key/HMAC provisioning documentation (readiness blocker 6) — the
   phone node cannot be provisioned repeatably without it. → M9.
8. `bridge_server.py` test-coverage gap (readiness blocker 11) —
   subsumed: rather than writing tests for a component being retired, M6
   wires its replacement and Section 6 gates its retirement on measured
   non-use; if the trial FAILS and bridge_server stays, then the coverage
   debt returns as a P5 obligation. [RECOMMENDATION]

**Outcome-driven (acts on the demo result, not a contributor — executed
at M12, ADR-014 review):**

9. `jarvis_core` freeze + the four deprecated shim removals (closure item
   7, C5) — the freeze is P4's ADR-014 charter, gated on the trial
   outcome; the shims are part of finishing that freeze. → M12.
10. `tools/` conflict (readiness blocker 4) — conditional, see Section 6;
    resolved only if the dispatch bridge touches it, else deferred to P5.

**Can wait until Priority #5+ (fails the "serves the demo" test AND is not
gated on the demo outcome):**

11. **Pure dead-code hygiene** — Brain `models/{reranker,router}.py`
    deletion and `easytool/`/`taskbench/` removal (closure item 8). Cheap,
    but contributes nothing to the demo and isn't gated on it; deferred to
    P5 per the freeze test (Section 5, "Deferred to Priority #5").
12. **`authority_scope` envelope field** — §5-completeness gap the demo
    never exercises; belongs with T2 work. Deferred to P5 (Appendix A #6,
    Section 5).
13. Dashboard sticky ping-result cosmetic glitch (closure item 4) — the
    P4 dashboard console (M10) reworks that panel anyway; if the glitch
    survives M10 it stays cosmetic.
14. MQTT TLS + per-node ACLs + broker auth (roadmap P2/P3 items; I12) —
    real hardening, but Tailscale is the current encryption boundary and
    the threat model is single-operator LAN; sequencing it into P4 would
    grow the priority beyond its keystone purpose. Revisit at P5 alongside
    any exposure change. [RECOMMENDATION]
15. Telegram gateway migration, `jarvis_prod` scheduler adoption, EventBus↔
    MQTT generalization, richer memory consolidation of device history.

---

## 8. Risk Assessment

| # | Risk | Probability | Impact | Mitigation |
|---|---|---|---|---|
| R1 | **The phone node's first-ever live Tailscale deployment is flaky** (nothing in either repo has ever run live over Tailscale; Termux sleep/Doze is a known hazard per jarvis_prod's own docs) and poisons the trial with infrastructure failures misread as architecture failures | High | High — a failed trial defers all retirements | Deploy the phone node mid-priority (M9), not last; burn it in before the trial begins; count infrastructure-caused failures separately from command failures in the outcome report; legacy stack stays available throughout per C2 |
| R2 | **Cognition quality**: Brain's planner (local LLM) misparses daily commands that the legacy stack's Claude-API prompt handled well, degrading real-world reliability | Medium | High | The demo command list is narrow and enumerable; add a deterministic intent→skill mapping layer for the confirmed list with LLM fallback [RECOMMENDATION]; measure parse accuracy separately during M11 before the trial begins | 
| R3 | **Security regression**: new consequential endpoints (invoke, approve) ship before scope enforcement, repeating the `/ping` pattern at higher stakes | Medium (institutional habit of deferral) | Critical | M1 is sequenced first and is a hard gate: no dispatch-bridge merge while any route lacks scope checks; C10/C11 tests are demo success criteria, not optional |
| R4 | **Contract lockstep break**: `ChimeraEnvelope` has `extra="forbid"`, so an old vendored copy *rejects* envelopes carrying the new optional fields — "optional" is additive per C13 only if both sides update together | Medium | Medium — silent verification failures | One coordinated M2: change canonical, re-run sync script, update both suites in the same milestone; live spot-check before any dependent milestone; document the lockstep requirement in the contract header |
| R5 | **Scope creep disguised as progress** (the roadmap's own dominant risk): dispatch invites "just one more skill / a routine engine / voice while we're here" | High | Medium — priority never closes | Section 9 is normative; any addition requires editing this document first; milestone list is closed-ended with a defined demo |
| R6 | **Kernel-bypass temptation**: wiring `pc.*` through root `core/` is harder than shelling out directly, inviting a "temporary" bypass that violates NP-8 | Medium | Critical (defeats defense-in-depth) | M6's completion criterion is the kernel-refusal demonstration itself — a bypassed kernel cannot pass it |
| R7 | **Trial honestly fails** (usage friction, latency vs ADB) | Medium | Low architecturally — C3 treats failure as data | Outcome report distinguishes architecture vs UX vs infra causes; ADR-014 review defers retirement with evidence; no sunk-cost forcing |

---

## 9. Out-of-Scope (normative)

Not in Priority #4, regardless of convenience:

1. **Voice interface** (wake word, STT/TTS surfaces) — vision-level work;
   nothing in C1–C16 requires it; the demo input surface is the dashboard.
2. **Vision/camera nodes and any new hardware nodes** (OPPO, Vivo,
   Arduino, ESP32, salvaged tablet display) — the demo needs exactly two
   nodes (PC + Nothing Phone). Hardware expansion is CLAUDE.md roadmap
   Phase 3/4 territory, post-P4.
3. **Multi-step scene automation / routines / schedules** ("I'm headed to
   bed" chains, cron-style jobs) — this is the "advanced automation"
   excluded by the capstone lineage; single-request, single-skill (or
   strictly per-request planned short sequences) only. The Telegram
   gateway and `jarvis_prod` scheduler migrations stay parked.
4. **T2 federation / node handoff / remote Brain** — explicitly deferred
   by §7 until T2 is actually built.
5. **EventBus↔MQTT general integration** — the dispatch bridge may
   *publish* to the existing in-process bus, but no generalized
   event-mirroring layer.
6. **Cognition refactoring** beyond the dispatch seam — no planner
   rewrite, no memory-architecture work, no knowledge graph.
7. **`hugginggpt/web` rebuild / thin-client expansion** (roadmap Phase 6).
8. **MQTT TLS, per-node ACLs, broker authentication** (Section 7, item 12).
9. **Deleting anything whose gate hasn't objectively passed** — retirement
   is Section 6's checklist, never a side effect.
10. **New ADRs** — per the closure precedent, P4 executes and completes
    accepted decisions (ADR-011/013/014); if implementation genuinely
    surfaces a new architectural decision, it stops and goes to the
    maintainer rather than being decided in code.

---

## 10. Definition of Done

Priority #4 is complete only when **every** item below is checked, each
verifiable by inspection or a recorded artifact:

**Security & contract**
- [ ] Every protected Brain route enforces a scope check (grep: zero
      routes without one; tests prove 403 on missing scope).
- [ ] `ChimeraEnvelope` carries optional `request_id` and
      `authority_scope`; vendored copy regenerated and byte-identical to
      the canonical logic; both suites green.
- [ ] Two concurrent in-flight commands to the same node resolve correctly
      (test exists and passes).
- [ ] Approval flow satisfies all three C10 properties, each with a test.
- [ ] A Brain-authorized command was refused by an operator-configured
      node ceiling in a recorded live demonstration (C11).

**Capability & execution**
- [ ] Nodes publish signed capability declarations; Brain plans only from
      the registry (grep: no static skill table in Brain).
- [ ] Removing a declared skill removes it from the plannable set with
      zero Brain code change (recorded demonstration).
- [ ] ≥ 8 real phone skills and the demo's `pc.*` subset execute via the
      spine; PC skills pass through root `core/`'s kernel (its `_dispatch`
      no longer a stub).

**Operations**
- [ ] Production node entrypoint runs unattended ≥ 24h on PC (heartbeat
      log) and the phone node runs live over Tailscale.
- [ ] Two nodes concurrently connected and commanded in one session
      (recorded).
- [ ] Provisioning (API keys, HMAC, node identity) documented well enough
      that a fresh node can be added without reading source code.

**Keystone Demo & trial**
- [ ] Every 3.6 criterion demonstrated and recorded; every 3.7 criterion
      absent.
- [ ] The trial ran under real conditions with instrumentation until the
      outcome-based evidence in 3.6(2) existed (sustained adoption,
      demonstrated reliability, real conditions); the outcome report exists
      with per-command-class evidence — not closed on a timer.

**Retirement & closure**
- [ ] `jarvis_core-v1-cognition` tag exists; the four deprecated shims
      removed (M12).
- [ ] Each Section 6 gate evaluated in writing at the ADR-014 review —
      executed if passed, deferred-with-evidence if not.
- [ ] `memory_module.py`/`logging_utils.py` disposition recorded in
      JARVIS's decision log.
- [ ] `PRIORITY-4-CLOSURE.md` written (audits directory), Decision Log
      closure summary appended, JARVIS `CURRENT_STATUS.md` updated —
      matching the P1–P3 closure pattern.
- [ ] Both full test suites pass with zero regressions from the P3
      baseline (Brain ≥ 174, JARVIS node SDK ≥ 26 + skip).

---

## Appendix A — Identified documentation conflicts (for resolution, not silently chosen)

1. **`SECURITY_BASELINE_V2.md` does not exist** in either repo despite
   being referenced in the Priority #4 research briefing. Recommendation:
   acknowledge `SECURITY_MODEL.md` + Priority #1 closure as the baseline,
   or create the consolidated document at M12.
2. **Skill-catalog revival ownership**: assigned to Priority #3 by
   ADR-013/014 (`DECISION_LOG.md:116`, `:168`), excluded from Priority #3
   by the capstone spec. This document claims it for Priority #4 (Sections
   2c, 4.3); the Decision Log's P4 closure summary should record that
   transfer in one line at M12.
3. **`tools/` fate**: `BRAIN_V2_DESIGN.md` says stays; PHASE7/8 say
   retire; ADR-014 said delete without acknowledging the conflict.
   Resolution path in Section 6 — decided by the maintainer, not
   defaulted.
4. **`MASTER_ROADMAP.md` Phases 1–3 are superseded by ADR-011** but the
   document doesn't say so itself (it predates the ADR). Recommendation: a
   supersession note in the JARVIS roadmap at M12, cross-referencing per
   ADR-012 rather than rewriting history.
5. **`CHIMERA_ECOSYSTEM_ARCHITECTURE.md:22`** — "four independent
   implementations" vs three enumerated; cosmetic, fix or leave, but now
   on record.
6. **§5 envelope requirements vs `ChimeraEnvelope`**: the architecture
   requires `correlation id` **and** `authority-scope` per envelope
   (`:54`); the shipped envelope has neither. The correlation half is
   already on record as deferred-not-decided (C7); the authority-scope
   half was not previously flagged anywhere. **Per the freeze refinement,
   `authority_scope` is deferred to Priority #5** (it fails the "serves the
   demo" test — the demo never exercises it, and its natural home is T2
   federation); the correlation half stays in M2. This deferral is recorded
   here and in Section 5 rather than left implicit.
