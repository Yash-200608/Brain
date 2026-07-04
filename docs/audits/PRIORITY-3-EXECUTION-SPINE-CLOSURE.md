# Priority #3 Execution Spine — Closure Report

> Audit artifact, not a decision record. See [`../DECISION_LOG.md`](../DECISION_LOG.md)
> for the ADRs (011–014) this closure checks the project against, and that
> log's **Architectural Decision Summary — Priority #3 Closure** section for
> the decision-record-level summary. This document is the operational,
> evidence-based account of what was built, tested, and verified — it will
> go stale as Priority #4 proceeds, unlike the ADRs it checks against.

Companion to [`PRIORITY-2-READINESS-REVIEW.md`](PRIORITY-2-READINESS-REVIEW.md)
(the GO decision this closure fulfills) and
[`PRIORITY-3-MILESTONE-1-RETROSPECTIVE.md`](PRIORITY-3-MILESTONE-1-RETROSPECTIVE.md)
(the only other Priority #3 artifact written before this one — a
per-milestone deep-dive on Milestone 1 specifically, not superseded by this
document).

## Governing specification

Priority #3 was declared complete against a specific, user-authored
completion criterion (the "Execution Spine Capstone"), obtained mid-priority
via an explicit clarifying question once milestone-by-milestone work
transitioned to autonomous continuation. Verbatim:

> Stop at the Execution Spine Capstone. Consider Priority #3 complete when
> the execution spine is operational end-to-end: Brain maintains the device
> registry and authenticated device state. JARVIS nodes can register,
> publish presence/state, receive authenticated commands, and return
> authenticated responses. Brain exposes a read-only API for inspecting
> registered devices and their current state. A minimal dashboard can
> display live device information and demonstrate the complete execution
> flow. The full end-to-end path (Dashboard/API → Brain → MQTT → JARVIS →
> Response → Brain → Dashboard/API) is demonstrated with at least one real
> command. All milestones remain independently tested, with the full suite
> passing and no regressions. Documentation (ADRs, architecture, and
> operational docs) reflects the implemented system. Do not automatically
> continue into skill/task orchestration, EventBus integration beyond what
> the spine requires, cognition refactoring, jarvis_core retirement,
> advanced automation, or other Priority #4 work.

Every bullet below is checked against that specification directly, not
against a looser interpretation of "execution spine."

## Milestones shipped

| # | Title | What it proved |
|---|---|---|
| 1 | Spine Foundation | Signed `ChimeraEnvelope` contract (Brain, canonical), vendored copy (JARVIS), node SDK extraction, `chimera/*` topic rename |
| 2 | Brain speaks MQTT | `BrainMqttClient`, inert-by-default lifespan — zero behavior change with MQTT off |
| 3 | Signed-envelope/MQTT composition | `mqtt/signed.py` proves `ChimeraEnvelope` + `BrainMqttClient` compose correctly, incl. real JSON wire round-trip |
| 4 | Device Registry | `Brain/devices/` — `Device`/`DeviceStore`, derived `is_online()`, fully MQTT-agnostic |
| 5 | Presence Subscriber | First real MQTT→DeviceStore wiring; `+`-wildcard dispatch added to `BrainMqttClient`; found+fixed an empty-segment matching bug before shipping |
| 6 | First Command/Response Round Trip | Proved via hand-built dicts (no live wiring yet); found+fixed a Milestone-1 vendoring bug (`ast.parse()` missed a future-import-placement `SyntaxError` that `compile()`/a real import caught) |
| 7 | Device State Subscriber | `chimera/+/state` subscriber, opaque JSON state blob (no schema imposed until a real consumer needs one); found+fixed a real SQLite `ALTER TABLE` migration gap before shipping |
| 8 | Real Command Path Wiring | Real `subscribe()`/`publish()` wiring on both sides (not just isolated logic) via the established fake-broker dispatch-loop technique; hand-rolled `(verb, action)` correlation instead of adding a schema field |
| 9 | Read-Only Devices API | `GET /api/devices/`, `GET /api/devices/{node}`; scope-enforcement gap deliberately deferred (user-confirmed) with a `TODO(auth)` marker rather than an incremental fix |
| 10 | JARVIS Presence/State Publisher | Closed the last capstone gap: JARVIS could not yet *publish* signed presence/state — `presence_publisher.py` + `state_publisher.py` |
| 11 | Minimal Dashboard Device View | Static dashboard gained a devices panel consuming `GET /api/devices/`, verified live in-browser incl. both online/offline dot branches |
| 12 | Live End-to-End Demonstration | Real Mosquitto broker (anonymous, no credentials needed — corrects an earlier assumption), real ping round trip proven repeatedly via curl + dashboard + JARVIS logs; two real Windows/asyncio/uvicorn bugs and one test-isolation bug found and fixed along the way |

## Objectives completed, checked against the capstone spec

**"Brain maintains the device registry and authenticated device state."**
✅ `Brain/devices/` (Milestone 4) + the `chimera/+/presence`/`chimera/+/state`
subscribers (Milestones 5, 7), both requiring `verify_payload()` (HMAC +
timestamp-skew check) before any write reaches `DeviceStore`. Confirmed live
during Milestone 12: `GET /api/devices/` returned the real node's state
(`{"battery": 91, "cpu_pct": 8.2}`) moments after the JARVIS demo node
published it over the real broker.

**"JARVIS nodes can register, publish presence/state, receive authenticated
commands, and return authenticated responses."** ✅ `presence_publisher.py` /
`state_publisher.py` (Milestone 10) for the publish side;
`command_listener.py` (Milestone 8) for receive/respond. All four verified
live in Milestone 12 — the demo node ran continuously for 13+ minutes,
publishing a 15-second presence heartbeat without a gap and correctly
answering every one of 6+ real ping commands sent during that window.

**"Brain exposes a read-only API for inspecting registered devices and
their current state."** ✅ `GET /api/devices/` and `GET /api/devices/{node}`
(Milestone 9), both behind the existing fail-closed `AuthMiddleware`.

**"A minimal dashboard can display live device information and demonstrate
the complete execution flow."** ✅ Milestone 11's devices panel (node, online
dot, state) plus Milestone 12's Ping button, which triggers the full
Dashboard → API → MQTT → JARVIS → Response → Brain → Dashboard round trip
and renders the result inline. Verified live via the browser preview
multiple times.

**"The full end-to-end path ... is demonstrated with at least one real
command."** ✅ The "ping" dummy action (built in Milestone 6 specifically to
prove this exact path) round-tripped for real over the live local Mosquitto
broker, confirmed independently via curl, the JARVIS demo node's own logs,
and the dashboard UI, across more than a dozen individual round trips over a
13+-minute session.

**"All milestones remain independently tested, with the full suite passing
and no regressions."** ✅ Brain: 111 (Milestone 1 baseline) → 174 passed.
JARVIS `jarvis_node_sdk`: 0 (package didn't exist before Milestone 1) → 26
passed + 1 pre-existing skip. Every milestone's own verification step ran
the full suite, not just its new tests, and every milestone's git diff was
reviewed to confirm the changed-file set matched what was actually scoped.

**"Documentation ... reflects the implemented system."** ✅ This document,
the Decision Log's Priority #3 closure summary, and JARVIS's
`docs/context/CURRENT_STATUS.md` update (all landing in the same body of
work as this closure).

**Explicitly-excluded scope, confirmed NOT done:** no skill/task
orchestration framework (the "ping" action remains the sole dispatchable
action, unchanged since Milestone 6); no EventBus integration beyond the
spine's own MQTT client; no cognition refactoring; no `jarvis_core`
retirement (still exists, untouched, per ADR-014's "extraction first,
freeze after" sequencing — the freeze step is explicitly Priority #4+
work); no advanced automation (`state_publisher.py` is deliberately
one-shot, not a polling loop, precisely to avoid this).

## Real bugs found and fixed during Priority #3

Listed because each is a durable lesson, not just a fixed line of code:

1. **Milestone 1's vendoring script generated unimportable code, and its
   own verification (`ast.parse()`) didn't catch it** — `ast.parse()` does
   not enforce `from __future__ import` placement rules; only `compile()`
   or a real `import` does. Found in Milestone 6. Lesson generalized:
   verify generated code with the mechanism that will actually consume it.
2. **A real SQLite migration gap** (Milestone 7) — `CREATE TABLE IF NOT
   EXISTS` is a no-op against an already-existing table; adding columns to
   an existing `devices` table needed a `PRAGMA table_info` + guarded
   `ALTER TABLE` migration. Found and fixed before shipping, via a
   dedicated test building a raw legacy database by hand.
3. **An empty-segment wildcard-matching bug** (Milestone 5) — the
   originally-proposed `_topic_matches()` let `+` match an empty topic
   segment (`chimera//presence` would incorrectly satisfy
   `chimera/+/presence`). Found via adversarial verification before any
   code was written.
4. **uvicorn hardcodes `ProactorEventLoop` on Windows, silently ignoring
   `asyncio.set_event_loop_policy()`** (Milestone 12) — confirmed by
   reading uvicorn 0.49.0's source: `asyncio_loop_factory()` returns
   `asyncio.ProactorEventLoop` unconditionally on `win32`, and
   `Server.run()` passes that factory straight to
   `asyncio.run(loop_factory=...)`, bypassing the global policy entirely.
   `aiomqtt` needs `add_reader()`/`add_writer()`, which `ProactorEventLoop`
   doesn't implement. Real fix: `uvicorn.run(..., loop=asyncio.
   SelectorEventLoop)` — uvicorn's `loop=` parameter accepts a bare factory
   callable, not just the `"auto"/"asyncio"/"uvloop"` string presets. Note
   this exact class of bug was already known and fixed once before, in a
   different component: JARVIS's own `docs/context/DECISION_LOG.md` ADR-004
   documents `brain_pc.py` forcing `WindowsSelectorEventLoopPolicy` at
   import time for the identical `aiomqtt`-on-Windows reason. The lesson
   didn't transfer to Brain automatically because Brain uses uvicorn
   (which needed the different, non-obvious fix) rather than a bare
   `asyncio.run()`.
5. **`Brain/.env`'s live-demo MQTT flag leaked into the test suite's
   default state** (Milestone 12) — `Settings` reads `.env` at import time,
   so enabling `JARVIS_MQTT_ENABLED=true` for the live demo caused any test
   that builds `TestClient(app)` without explicitly monkeypatching
   `mqtt_enabled` (e.g. the test proving the *disabled* case) to silently
   attempt a real broker connection instead, hanging the suite. Fixed with
   the same `os.environ.setdefault(...)` pattern `tests/conftest.py`
   already used for `JARVIS_GOALS_DB`/`JARVIS_DEVICES_DB`, etc.
6. **The local Mosquitto broker needs no credentials at all** — corrects an
   earlier assumption (recorded, then corrected, in project memory) that
   live-broker work would need to pause and ask the user for
   username/password. A direct anonymous `paho-mqtt` probe proved otherwise
   before any milestone work was blocked on it.

## Remaining technical debt, by severity

**High priority (should be resolved before or during Priority #4's first
real device-action work):**
1. **No scope enforcement (`has_scope()`) on any route**, including the new
   `POST /api/devices/{node}/ping` — deliberately deferred twice now
   (Milestones 9 and 12) per explicit user direction, to avoid
   incrementally patching one route at a time. `PRIORITY-2-READINESS-REVIEW.md`
   already named "device-level actions" as the trigger; `/ping` is now
   exactly that trigger, twice over. A future milestone should wire scope
   enforcement across every protected route in one coherent pass.
2. **`send_command_and_await_response()` has no `request_id`/correlation
   field** — matching on `(verb, action)` is sufficient for the single
   in-flight command this spine ever sends, but is not safe for concurrent
   overlapping commands to the same node+action. A schema change to
   `ChimeraEnvelope` was explicitly considered and rejected twice (Milestones
   6 and 8) as disproportionate to a one-command spine; Priority #4's
   skill/task dispatch work (explicitly out of this priority's scope) is
   the natural point to revisit this if concurrent commands become real.
3. **Repeated calls to `send_command_and_await_response()` on the same
   client accumulate handlers on `chimera/{node}/response`** — each
   `subscribe()` call appends to a list rather than replacing; harmless
   today (each stale handler's `future.done()` guard makes it a no-op) but
   an unbounded-growth risk under sustained real traffic, not just the
   handful of pings this closure demonstrated.

**Medium priority (worth fixing, not blocking):**
4. **The dashboard's sticky ping-result display can occasionally revert to
   blank** after several minutes of accumulated 30-second poll cycles
   (Milestone 12) — the underlying fix (a per-node result `Map` restored on
   every re-render) is correct in principle and was confirmed working
   immediately after a ping; a residual case where it still reverts wasn't
   conclusively root-caused in this session. Re-clicking Ping always
   immediately shows the correct result — this is a display nicety, not a
   functional defect.
5. **`jarvis_node_sdk`'s command/presence/state modules have no auto-start
   wiring into any real JARVIS entrypoint** — `run_chimera_demo_node.py`
   (Milestone 12) is explicitly a demo/proof script, not a production
   runner. A real always-on JARVIS node process (with real config sourcing
   for the HMAC key and node identity, not CLI flags) is Priority #4-or-later
   work.
6. **Single-node demonstration only.** The spine has never been proven with
   two or more concurrently-connected JARVIS nodes, multiple devices
   competing for the same broker, or a node reconnecting mid-session. The
   presence heartbeat and command listener are both designed to support
   this (no node-count assumptions anywhere in the code), but it has not
   been exercised.

**Can wait (pre-existing, not introduced by or blocking Priority #3):**
7. `jarvis_core`'s cognition modules remain unretired (git-tag-and-freeze
   per ADR-014 is still pending — explicitly out of this priority's scope
   by the capstone spec itself).
8. `easytool/`/`taskbench/` removal, Brain's `models/{reranker,router}.py`
   deletion, `hugginggpt/server/jarvis/*` skill-framework archival — all
   already listed as deferred in `PRIORITY-2-READINESS-REVIEW.md`, still
   deferred, unaffected by anything in this priority.

## Recommendations for Priority #4

1. **Resolve scope enforcement in one coherent pass** before adding any
   further device-level action beyond `/ping` — this is the single most
   flagged, most deferred item across three milestones now (9, 12, and the
   original Priority #2 readiness review).
2. **If Priority #4 introduces skill/task dispatch** (explicitly out of
   Priority #3's scope), that is also the right moment to revisit the
   `request_id`/correlation-ID question for `ChimeraEnvelope` — concurrent
   commands are exactly the scenario the current `(verb, action)` matching
   doesn't safely support.
3. **Build a real, always-on JARVIS node entrypoint** (config-sourced HMAC
   key + node identity, not CLI flags) once there's a concrete reason to
   run one continuously — `run_chimera_demo_node.py` is deliberately not
   that, and shouldn't be mistaken for it.
4. **Prove multi-node operation** at least once before designing anything
   that assumes it works (fleet dashboards, cross-node orchestration,
   etc.) — today's evidence is exactly one node, one command type, one
   broker, one session.
5. Continue the standing practice from Priority #3: small, independently
   verifiable milestones, full-suite verification after each, and
   adversarial/direct verification of any load-bearing claim before
   committing to a design — this discipline caught six real bugs across
   twelve milestones before or immediately after they would have shipped
   silently broken.

## Verdict

**Priority #3 is CLOSED.** Every capstone bullet is satisfied with direct,
reproducible evidence (curl, live logs, and interactive dashboard use, not
mocked). No explicitly-excluded scope was touched. Both repos' full test
suites pass with zero regressions (Brain 174/174, JARVIS 26/26 + 1
pre-existing skip). Six real bugs were found and fixed along the way, three
of them (the vendoring `SyntaxError`, the SQLite migration gap, the
wildcard-matching gap) before they ever shipped, and three (the two
Windows/asyncio bugs and the test-isolation leak) within the same milestone
that surfaced them. Remaining technical debt is enumerated above by
severity, not hidden — the highest-priority item (scope enforcement) has
been flagged three times now and should be Priority #4's first order of
business before any further device-level action is added.
