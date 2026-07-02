# CHIMERA ECOSYSTEM ARCHITECTURE

## 0. Status and Purpose

This is the canonical, top-level architecture reference for the Chimera ecosystem (Brain + JARVIS + future participants). It is the document all other architecture decisions derive from: ADR-011 (Brain-as-cognitive-authority), the protocol namespace ADR, Brain's security-model remediation plan, and future ADRs must be consistent with it, not the reverse.

It intentionally does not decide: which MQTT topic string to use, which specific files get renamed or retired, which specific tests must pass before what date, or the literal JSON Schema for the envelope. Those are implementation and ADR-level decisions, made in service of the principles below, and free to change without revising this document. Where this document requires a concrete artifact to exist (a schema, a conformance suite), it says so explicitly and treats the artifact as a pointer this document owns, not content this document contains.

Durability test for every claim in this document: would it still be true if Brain were rewritten from scratch in a different language, or if JARVIS were replaced by a different embodiment platform entirely? If not, it doesn't belong here.

## 1. The Organizing Principle

Chimera separates COGNITION from EMBODIMENT as a hard architectural boundary, not a convention:

- **Cognition** = deciding what should happen: planning, memory, reasoning, orchestration, goal management, reflection. Exactly one authority owns this per deployment: Brain.
- **Embodiment** = making things happen and reporting what happened: sensing, acting, rendering, safety enforcement at the point of action. Any number of embodiment platforms may exist; JARVIS is the first and flagship one.

**The boundary is functional, not a proxy for model size or reasoning complexity.** A component remains an embodiment participant — regardless of how sophisticated its on-device inference is — as long as its outputs are limited to capability/state declarations and execution of Brain-authorized action shapes. A component becomes a cognition authority only when it originates new goals or persists cross-session planning state on its own initiative. A node that chains several on-device model calls to answer "is this a known face" and reports the answer as state is embodiment; a component that decides *what to do* about the answer without Brain having authorized that decision shape in advance is cognition, however small its model is. This test is what makes "never both" enforceable by rule rather than by intuition.

**"Brain" denotes an authority boundary, not a mandated single process.** If Brain is later decomposed into multiple internally-deployed cognitive services (a planning service, a reflection service, an identity-policy service), that decomposition is Brain-internal evolution under Section 9, invisible to embodiment platforms, as long as the boundary presents one coherent decision per request. "Brain is live" (referenced by Section 4) means the authority boundary as a whole is live, with degradation rules for partial-internal-failure left to Brain's own internal design — never a claim about any specific internal process.

A component is either a cognition authority or an embodiment participant — never both. This is the rule four independent implementations violated before this document existed (the legacy stack, jarvis_prod's brain_pc.py, and jarvis_core all embedded planning inside an embodiment surface). Any future component inherits this rule by construction, not by convention.

## 2. System Boundary Model

Brain and JARVIS (and any future embodiment platform) are independently deployable services, in independent repositories, with independently chosen languages, runtimes, and release cadences. What is fixed across the boundary is the CONTRACT (Section 5) — not code. No component may import, subclass, or directly call into another component's internals across this boundary. This is a peer-service model, not a plugin model: Brain does not "host" JARVIS, and JARVIS does not "embed" Brain. Either can be deployed, tested, and evolved without the other being present (with degraded capability, per Section 4).

A **deployment** is the scope governed by exactly one authoritative Brain boundary at a given time, identified by the authority-scope field in the envelope (Section 5). Multiple deployments (e.g., federated per-household Brain instances, Section 7's T2) may exist; a node belongs to exactly one deployment at a time. Transfer of a node between deployments (handoff) is a real future need this document does not yet fully specify — see Section 7.

## 3. Actors

- **Brain** — the sole cognitive authority for a given deployment (an authority boundary, per Section 1 — not necessarily one process). Owns: memory (all tiers), planning, agent orchestration, goal state, reflection, identity/authorization POLICY.
- **Embodiment platforms** (JARVIS is the reference implementation) — own: device/OS/hardware integration, user-facing interaction surfaces, and the ENFORCEMENT of safety policy at the point of action. Never originates multi-step plans; executes tasks Brain dispatches, or bounded/locally-sovereign local behaviors it's been authorized to run unattended (Section 4).
- **Nodes** — addressable units within an embodiment platform's device mesh. Advertise capabilities and state; do not decide what to do with them beyond the local-autonomy scope of Section 4, per the functional test in Section 1.
- **Clients** — thin interaction surfaces that render Brain's state and relay user input. Never reason.
- **Future cognitive participants** — this document explicitly anticipates Brain may one day serve embodiment platforms other than JARVIS, or that multiple Brain instances (deployments) may exist, federated per-household or per-organization. Nothing assumes JARVIS is Brain's only or permanent consumer.

## 4. Local Autonomy

Embodiment platforms may act without a live decision from Brain in two distinct forms — conflating them was an earlier error in this document, since they have different latency and trust requirements.

**4a. Reactive bounded autonomy** — for resilience during disconnection, not for latency-critical paths. Requires all of:
1. **Authored by Brain, cached at the edge.** Rules a node may act on unattended are declared and versioned by Brain, not invented locally.
2. **Health-gated.** A node enters this mode based on an observed Brain-liveness check (of the authority boundary, per Section 1), never on an assumption about machine co-location — same-machine deployment does not imply same-availability, since Brain can fail independently of the machine or other local services.
3. **Time-bounded.** Every cached rule set carries an explicit expiry/epoch issued by Brain. A node whose cache has exceeded its validity window degrades to its minimum-safe default regardless of what the liveness check says, and must reacquire fresh rules (or observe an explicit revocation) before resuming. Safety-relevant (high-risk) rules carry materially shorter TTLs than low-risk ones. This is what makes revocation possible: liveness alone only detects "Brain is down," never "Brain's prior authorization is no longer valid."
4. **Reconciled, not silent.** Every action taken under this mode is logged locally and replayed to Brain on reconnect for audit and memory consolidation. A node's local state is never the system's source of truth beyond the disconnection window.

**4b. Locally-sovereign safety actions** — for action classes where even a successful liveness check is unacceptable latency (a safety interlock that must resolve in single-digit milliseconds, independent of whether Brain is reachable at all). These are still authored and versioned by Brain (property 1 above) and still reconciled after the fact (property 4), but are explicitly exempt from the liveness gate (property 2) by design — the node never checks, it always has local authority for this specific, narrowly-scoped action class. Declaring an action class as locally-sovereign is itself a Brain-authored, versioned decision, not a node's own choice.

Both forms exclude: multi-step planning, memory formation beyond the local action log, and any decision Brain hasn't pre-authorized the shape of — per the functional cognition/embodiment test in Section 1.

## 5. Communication Contract

- **Envelope.** Every message crossing the boundary is a signed, versioned envelope: sender identity, authority-scope (which Brain deployment this message belongs to, Section 2), message type, schema version, correlation id, timestamp, and a signature over all of the above (HMAC-with-nonce-and-skew-window as baseline). Unsigned or unverifiable messages are rejected at the boundary — see the fail-closed invariant, Section 6.1.
- **Capability declaration, not hardcoded skill lists.** Every embodiment participant advertises what it can do and its current state; Brain builds its plan of available actions from live declarations, never a static table baked into Brain's code.
- **Risk taxonomy.** One risk-tier enum with a defined total order, referenced by the planner, the node's declared risk ceiling, and the embodiment platform's local safety kernel. Every consumer of this enum MUST fail closed on an unrecognized or future tier value (treat unknown as maximum restriction, never as permissive) — this is what makes adding a new tier later safe (Section 8). Where the enum is schema-defined (which repo owns the package) is an ADR-level detail.
- **Approval flow.** A destructive or risk-gated action's approval must: (1) originate from a principal distinct from, and privileged above, the action's requester — never the same caller in a different field of the same request; (2) be verified against the action's already-computed risk tier before any execution or safety-rewrite step runs — risk classification always precedes and gates any rewrite, never the reverse; (3) be single-use and bound to that specific action instance, not replayable against a different action under the same identifier.
- **Conformance.** This document states principles, not a literal schema. A concrete, versioned schema and conformance test suite is the actual compliance artifact for "implements the contract" (Section 9) — this document commits to that artifact existing at a stable, referenced location once written; a peer cannot claim conformance from this text alone.
- **Out of scope by design:** the specific transport (MQTT today; could change), the specific topic grammar, the specific broker topology, and node-to-node handoff/federation mechanics (Section 2) — belong in dedicated ADRs.

## 6. Trust & Security Boundary

1. **Fail-closed is the default, always.** Any request whose identity, signature, or authorization cannot be positively and successfully verified MUST be rejected — never defaulted to a privileged, anonymous, or "trusted for now" identity. Verification failure is not a distinct trust tier; it is rejection. This invariant is referenced, not restated, by Section 5's approval-flow rule and Section 8's enum-versioning rule — anywhere ambiguity could otherwise resolve toward permissiveness, it resolves toward restriction instead.
2. **No implicit trust across the boundary.** Brain does not trust a node because it's "on the mesh"; a node does not trust a command without verifying identity end-to-end, per invariant 1.
3. **Network exposure is minimized independently of message-layer authentication.** A signed-envelope requirement (Section 5) says nothing about which interfaces or origins may reach a service before envelope validation even runs. Every service binds to the narrowest interface its deployment topology (Section 7) actually requires, and any browser-reachable surface enumerates explicit allowed origins — wildcard exposure is never a default.
4. **Authorization-relevant fields are authority-assigned, not client-supplied.** Scope, role, and risk-ceiling values are assigned exclusively by Brain's policy layer (or, for a node's own declared ceiling, by whoever operates that node — see invariant 5) and are structurally rejected if present in inbound payloads from the untrusted side of a given boundary — never merged, defaulted, or coalesced from caller input. "Traceable end-to-end" (the general principle) means these values can be traced to their authoritative origin, not merely that they survive the trip unmodified.
5. **Defense in depth has an independent root of trust.** Brain's authorization decision is necessary but never sufficient. Every embodiment platform enforces its own safety kernel on every dispatched action — and for the highest risk tier(s), that kernel's ceilings and irreversible-action gates are operator-configured at the embodiment platform and are not modifiable by any Brain-originated message, signed or not. The highest tier(s) require a confirmation channel Brain cannot itself satisfy (e.g., local human-present confirmation). Without this, "last line of defense even against a compromised Brain" is not achievable — a compromised-but-correctly-signed Brain could otherwise issue its own permissive ceiling and defeat a kernel that only checks Brain's signature.

## 7. Deployment Model

- **T0 — single machine** (today): Brain, broker, and one embodiment platform's hub node share a box.
- **T1 — hub and mesh**: Brain and broker centralized; embodiment nodes distributed across phones/microcontrollers/displays.
- **T2 — multi-Brain / federated / remote Brain**: Brain relocated off-box, or multiple Brain deployments (Section 2) exist for different households/scopes.

No component may assume T0. T2 introduces a real, currently unsolved problem this document names rather than hides: a node moving between deployments (e.g., a roaming device) needs a defined handoff — which deployment's authorization is canonical during the transition, how a node arbitrates two simultaneously-reachable Brain boundaries, and how previously-cached local-autonomy rules (Section 4) are invalidated on handoff. The authority-scope envelope field (Section 5) and the time-bounded cache requirement (Section 4a-3) are the minimum primitives a handoff protocol will need; the protocol itself is deferred to a dedicated ADR, written when T2 is first actually built, not invented speculatively here.

## 8. Versioning Strategy

The contract evolves under semantic versioning, with shape-stability and trust-semantics treated as separate axes:

- **Shape changes are version-scoped.** A new *optional* field is additive and may ship within a major version. A new *required* field is always a major-version bump, since old declarations become invalid against it — Section 9's "no Brain-side code change for a new node" claim applies only to nodes conformant with the current major, not universally.
- **Enum additions are conditionally additive.** Adding a value to a shared enum (e.g., a new risk tier) is non-breaking only for consumers that implement the fail-closed-on-unrecognized-value rule (Section 6.1/Section 5). A consumer that does exhaustive matching or defaults unknown values permissively must treat the addition as breaking for itself.
- **Security-motivated trust withdrawal is not the same as a shape change.** Brain may stop *trusting* the semantic meaning of a field (e.g., stop honoring a node's self-declared `risk_ceiling`) within a minor version, while still syntactically accepting the field for the remainder of any deprecation window — logged and audited. Waiting for a full major-version deprecation cycle to close a live security hole is not required.
- **Negotiation is per-connection.** Each connection negotiates its own mutually-supported version independently; Brain may hold multiple concurrent per-connection version contexts. If no mutually-supported version exists, the connection is rejected outright, not silently degraded.
- **Support is bounded, never open-ended.** Every Brain deployment publishes an explicit, bounded support window (e.g., current major plus one prior) and a minimum-supported-version floor below which connections are rejected. "Additive-only" is a policy for evolution *within* that bounded window, not a promise to serve every version ever declared, forever.

## 9. Extensibility Model

- A new node type implements the contract's capability-declaration and envelope-signing requirements and is automatically plannable — no Brain-side code change required, for any node conformant with Brain's currently-supported major version (Section 8).
- A new embodiment platform (not JARVIS) is a peer, not a special case: it implements the same published, versioned schema and conformance suite (Section 5) that JARVIS does. Brain's design must not special-case "the JARVIS client" anywhere in its authority logic.
- A new cognitive capability, including Brain's own internal decomposition into multiple services (Section 1), is Brain-internal evolution and does not require embodiment-side changes, as long as the contract surface (Section 5) and the authority-boundary liveness semantics (Section 1) are preserved.

## 10. What Supersedes What

Where this document conflicts with prior planning artifacts in either repo (Brain's PHASE7/PHASE8 blueprint, or JARVIS's `SYSTEM_ARCHITECTURE.md` / `BRAIN_SPEC.md` / `BRAIN_CONSTITUTION.md`), this document's ownership and boundary conclusions are authoritative. Their concrete file-level analysis remains useful implementation guidance and should be cited, not discarded, when derived ADRs and implementation plans are written.

This document does not itself resolve ADR-011, the namespace question, Brain's security remediation plan, the concrete envelope/risk-taxonomy schema, or the T2 federation/handoff protocol — those are derived artifacts, written next, and must be consistent with, but are not part of, this document.
