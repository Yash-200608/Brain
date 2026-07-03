# Priority #2 Implementation Readiness Review

> Audit artifact, not a decision record. See [`../DECISION_LOG.md`](../DECISION_LOG.md) for the ADRs (011–014) this review checks the project against. This document is an operational snapshot at Priority #2's close, not architecture — it will go stale as Priority #3 proceeds, unlike the ADRs it references.

Companion to [`ADR-014-DEPENDENCY-ANALYSIS.md`](ADR-014-DEPENDENCY-ANALYSIS.md), performed as the final operational-closure pass before Priority #3 (execution spine) begins.

**Is Brain ready for the execution spine?** Yes, to start. Cognition loop runs (87/87 tests green); auth is fail-closed and verified end-to-end including the real dashboard round trip; ADRs 011–014 give the spine unambiguous direction. Gap, not blocker: zero MQTT/connectivity code exists yet (`devices/`, `mqtt/` don't exist) — that absence is the very thing Priority #3 builds, not a precondition unmet. Caveat: new spine components must be built to ADR-013's stated standard (signed envelopes, fail-closed) rather than inheriting Brain's still-open scope-enforcement gap (`has_scope()` is resolved but never checked by any route).

**Is JARVIS ready for the execution spine?** Conditionally. The safety kernel's confirmed ordering bug is fixed and tested (34/34). But the dependency analysis found a confirmed, unfixed bug directly in the node-SDK candidate's critical path: `signing.py` signs before `transport.py` injects `request_id`, so every signed phone command fails verification today. Building the spine's signed envelope on top of this without fixing it first ships a broken security property. Root `core/`'s `_dispatch` is also still a stub — the safety kernel gates correctly in tests but doesn't yet invoke anything real.

**Priority #1 regressions:** none outstanding. Two were found and fixed during dashboard-restoration verification (CORS preflight rejected by AuthMiddleware; unhandled exceptions losing CORS headers) — both have permanent regression tests now. Re-verified clean: Brain 87/87, JARVIS `core/`+`tests/` 34/34, `jarvis_core` 8/8 (+1 pre-existing unrelated skip).

**Priority #2 inconsistencies:** two found and corrected — ADR-014's path misattribution (`memory_module.py`/`logging_utils.py` don't exist in Brain) and its imprecise `§6.5` citation. Both amended in the Decision Log and detailed in the dependency analysis, not silently rewritten.

**Operational blockers:** none remaining. Dashboard auth restored and verified. Ollama unavailability in this dev environment is a documented limitation, not a code defect.

**Migration blockers:** the three "Requires migration first" items from the dependency analysis (node SDK, `brain_pc.py`, `jarvis_prod` infra) are not blockers to *starting* Priority #3 — they are Priority #3's necessary first steps, already sequenced that way by ADR-014 itself ("extraction first, freeze after").

**Implementation blockers:** none that block starting; two must be resolved as part of the earliest spine work (below).

## Blockers, by severity

**Critical (resolve as Priority #3's first steps, not deferred):**
1. Fix the HMAC signing-order bug (`jarvis_core/core/signing.py` + `transport.py`) before or as part of node-SDK extraction.
2. Resolve `_smoke.py`'s direct `from brain_pc import Brain` coupling as part of the ADR-013 namespace migration, so the only integration test either repo has doesn't silently break.

**High priority (resolve early in Priority #3, not blocking day one):**
3. Implement real dispatch handlers for root `core/`'s `_dispatch` stub.
4. Resolve Brain's internal disagreement over `tools/`'s fate (`BRAIN_V2_DESIGN.md` "stays" vs. `PHASE7`/`PHASE8` "retire") before building anything that assumes either outcome.
5. Wire actual scope enforcement (`has_scope()`) into Brain's routes before the spine adds device-level actions with real consequences.
6. Document the API-key provisioning process (currently a one-off local `.env`) for future environments/deployments.

**Can wait until after Priority #3:**
7. `easytool/`/`taskbench/` removal.
8. `jarvis_core` cognition git-tag-and-freeze (once node-SDK extraction is done).
9. `hugginggpt/server/jarvis/*` skill-framework archival.
10. Brain `models/reranker.py`/`router.py` deletion.
11. Test coverage for `bridge_server.py` (real, pre-existing gap; not new, doesn't block spine architecture work).

## Recommendation: GO

Priority #3 may begin, with the two critical items above as its explicit first work items — not a separate remediation phase, but the actual starting sequence the execution spine requires regardless (you cannot build a trustworthy signed-envelope protocol on top of a signing implementation that's confirmed broken, and you cannot migrate the wire protocol without touching the file the only integration test imports). No blocker found in this review requires stopping and waiting before that work starts.
