# Priority #3, Milestone 1 Retrospective — Spine Foundation

> Audit artifact, not a decision record. See [`../DECISION_LOG.md`](../DECISION_LOG.md) ADR-013/014 for the architectural decisions this milestone implemented, and the [plan](file:C:/Users/Hp/.claude/plans/shiny-wiggling-melody.md) for the original scope. Engineering retrospective, not another architecture review — captures implementation knowledge before Milestone 2 begins.

## Objectives completed

All six deliverables from the approved plan shipped and are test-verified in
both repos:

1. Fixed the JARVIS signing-order bug (`jarvis_core/core/executor.py`).
2. Extracted `JARVIS/jarvis_node_sdk/` (signing, sandbox, transport, sensors
   + duplicated config/logging) out of `jarvis_core/core/`.
3. Executed the `chimera/<node>/<verb>` topic rename in
   `hugginggpt/server/jarvis_prod/protocol.py`.
4. Built Brain's canonical `protocols/chimera_contract.py`
   (`ChimeraEnvelope`, `RiskTier`, `sign()`/`verify()`).
5. Built `Brain/scripts/sync_chimera_contract.py`, run for real against the
   live JARVIS checkout.
6. Full verification checklist executed, including a real round-trip via
   the actual receiver (`phone_executor.verify()`), not just the sender's
   own `verify_envelope()`.

Two blockers named Critical by the Priority #2 Readiness Review are closed.

## Unexpected discoveries

- **`sensors.py` was miscategorized as cognition before this milestone.**
  It imports only `.transport`/`.config` plus `psutil`/`pygetwindow` and
  does pure sensing/publishing — no LLM, planning, or memory calls. Reclassified
  into the node SDK; `requirements.txt`'s "cognition-only" tag on
  `psutil`/`pygetwindow` is now slightly stale as a result (not fixed this
  milestone — noted, not silently left inconsistent).
- **A canonicalization mismatch exists between `transport.py`'s wire-publish
  format (`json.dumps` without `sort_keys`) and `signing.py`'s HMAC
  canonicalization (`sort_keys=True`).** Found by an adversarial
  verification pass before implementation, not during it. Confirmed
  harmless — `phone_executor.verify()` re-derives canonical bytes from the
  *parsed* dict, not from wire bytes — but the round-trip test now proves
  this with an actual `json.dumps`/`json.loads` hop rather than assuming it.
- **`config.py`'s `PROJECT_ROOT` computation could not be copied verbatim**
  the way the plan's shorthand ("duplicate config.py unchanged") implied.
  It's `Path(__file__).resolve().parent.parent`, which resolves differently
  depending on which directory the file physically lives in — the
  `jarvis_node_sdk/` copy needed `parent.parent / "jarvis_core"` added to
  keep pointing at the same YAML/`.env` files. A literal duplicate would
  have silently broken config loading.
- **A live Mosquitto broker is running on the dev machine, but its
  credentials are not stored anywhere in either repo** (by design). This
  reframes the `_smoke.py` gap: it's not "no broker infrastructure exists,"
  it's "credentials weren't available to this session" — a materially
  different, and easier, problem to close later.

## Architectural assumptions validated

- The chimera/* rename really was a single-file, single-source-of-truth
  change — `brain_pc.py`/`agent_phone.py` needed zero edits, confirmed by
  grep both before and after.
- The node-SDK/cognition boundary drawn by ADR-014's dependency analysis
  (`transport`/`signing`/`sandbox`/`phone_executor` vs.
  `brain`/`memory`/`scheduler`) held with only one addition (`sensors.py`).
- Brain's existing package convention
  (`models.py`/`service.py`+singleton, or here, a flat contract module
  matching `envelope.py`'s own shape) needed no adaptation for the new
  contract.
- `phone_executor.py`'s deliberate non-import of `core.signing` is a real,
  load-bearing design constraint (single-file Termux deploy), not
  incidental duplication — preserved correctly, and the signing-order fix
  was still achievable without touching it.

## Architectural assumptions disproven

- None of the six ADR-013/014 architectural decisions were found wrong
  during implementation. The one correction was procedural (see Lessons
  Learned), not architectural.

## Technical debt introduced

- **`jarvis_node_sdk/config.py` and `logging_setup.py` are now genuine
  duplicates** of `jarvis_core/core/config.py`/`logging_setup.py` (not
  shims — full independent copies), pending a shared `SdkConfig` extraction
  later. They can silently drift if one is edited and not the other.
- **`jarvis_node_sdk/chimera_contract.py`** (vendored, generated) has no
  test of its own — only the canonical Brain-side source is tested. Correct
  for now (it's generated, not hand-written logic), but means a bug in the
  sync script's *body-copying* step specifically (as opposed to its
  header-stamping, which is tested) would not be caught by either repo's
  test suite.
- **Four deprecated shim modules** now sit in `jarvis_core/core/`
  (`signing.py`, `sandbox.py`, `transport.py`, `sensors.py`), each a
  thin `from jarvis_node_sdk.X import *` re-export with a deprecation
  docstring — added after initial implementation per user review (see
  Lessons Learned). Intentional, temporary technical debt with an explicit
  removal trigger (once `jarvis_node_sdk` is proven stable in Milestone 2).

## Technical debt removed

- The signing-order bug itself (a live, wire-format-breaking security bug,
  not just a smell).
- The absence of any package boundary between JARVIS's node-infrastructure
  code and its cognition code — `jarvis_node_sdk/` is now real, testable,
  and independently reasoned about.
- `transport.py` had zero test coverage before this milestone; it now has
  targeted coverage of the exact behavior (`request_id` merge idempotency)
  the signing fix depends on.
- `hugginggpt/server/jarvis_prod/` had zero test coverage before this
  milestone (no `tests/` directory existed); it now has import-cleanliness
  and topic-format regression coverage.

## Lessons learned

- **Migrate, don't move, when a milestone is already introducing multiple
  simultaneous structural changes.** The plan specified move-then-delete
  for the SDK extraction; in retrospect, deleting `jarvis_core/core/`'s
  originals in the same pass that also introduced a new package, new
  imports, a new protocol, a new signed contract, and a topic rename
  increased this milestone's blast radius more than necessary — if
  Milestone 2 surfaces a bug, both behavior and structure would have
  changed together, making it harder to isolate which change caused it.
  Corrected post-implementation: the four originals are now deprecated
  re-export shims rather than deleted, preserving a fallback import path
  during Milestone 2's stabilization period. **Going forward: default to
  copy-then-verify-then-delete for any migration that lands inside a
  milestone already carrying other structural risk; reserve immediate
  deletion for milestones that are otherwise low-risk.**
- **Generated/vendored files should be named for what they *are*, not what
  they *aren't*.** A leading underscore reads as "private implementation
  detail" in Python convention; a canonical vendored contract is the
  opposite of that. An explicit `AUTO-GENERATED -- DO NOT EDIT` banner
  communicates "don't hand-edit" far more legibly than a naming convention
  borrowed from an unrelated meaning. Corrected: renamed
  `_chimera_contract.py` → `chimera_contract.py`.
- **Test-count totals ("111 passed") are a weaker signal than new-test
  counts and coverage gaps.** 35 tests were added this milestone (11
  JARVIS, 24 Brain); modules that remain untested going into Milestone 2
  include `jarvis_node_sdk/{config,logging_setup,sensors}.py`,
  `jarvis_core/core/{brain,memory,scheduler,ollama_client}.py`,
  `hugginggpt/server/{bridge_server,awesome_chat,device_integration}.py`,
  and — on the Brain side — `core/{planning,routing}.py`,
  `agents/workers.py`, `memory/{extractor,graph_builder}.py`,
  `models/{classifier,embeddings,reranker}.py`, and all of `tools/`. None
  of these are new gaps this milestone created; naming them explicitly
  here so they're visible going into Milestone 2 rather than implied by a
  passing-count headline.

## Changes to Milestone 2 sequencing

None to the milestone's scope or ordering. One process change carries
forward: **Milestone 2 (the MQTT bridge, EventBus↔transport wiring, and
envelope reconciliation) will default to copy-then-verify-then-delete for
any file relocation, and will be scoped for independent verifiability at
each step rather than landing as one large pass** — per explicit user
guidance following this milestone's review.
