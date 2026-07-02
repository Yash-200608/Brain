# PHASE 5 — HARDWARE INTEGRATION STUDY

> Turning the physical inventory into a Chimera node mesh, grounded in the
> MQTT/protocol code that already exists.
> Date: 2026-06-14 · Status: DESIGN STUDY · **No code changes.**
> Code anchors: `jarvis_prod/protocol.py`, `jarvis/schema.py` (wire + topics),
> `jarvis_core/core/transport.py` (MQTT client), `signing.py` (HMAC),
> `agent/phone_executor.py` (node template), `jarvis/pc_skills.py`/`phone_skills.py`
> (skill catalogs). Boundary follows Phase 4 (Brain = hub/cognition; nodes = I/O + actuation).

## Grounding: what the code already gives us

| Asset | File | Reuse |
|---|---|---|
| Node-keyed topic scheme `jarvis/node/{id}/{verb}` | `jarvis_prod/protocol.py` `class T`, `jarvis/schema.py` `class T` | **The standard to adopt** — already generalizes to N nodes. |
| Message envelope (Command/Response/Event/State/Request) | `protocol.py`, `schema.py` | The node↔Brain payloads. `State`/`Request` only in `schema.py` → merge. |
| MQTT client: reconnect, retained/QoS, wildcard fan-out, req/res RPC | `jarvis_core/core/transport.py` | Smart-node + Brain MQTT client. |
| Zero-trust signing (HMAC-SHA256, nonce+ts, 120 s skew) | `jarvis_core/core/signing.py` | Per-node message auth. |
| Termux node reference (LWT, retained heartbeat, allow-listed actuation) | `jarvis_core/agent/phone_executor.py` | Template for every smart node. |
| Skill catalogs (≈17 PC, ≈20 phone skills) | `jarvis/pc_skills.py`, `phone_skills.py` | Seed the HAL + device registry. |
| Heartbeat-staleness → alert | `jarvis_core/core/scheduler.py` | State-management pattern → Brain registry. |
| QoS-1 duplicate handling at actuator | `JARVIS/core/idempotency.py` | Exactly-once node execution. |

**Three naming conventions exist** and must be reconciled to one:
`jarvis/node/{id}/{verb}` (protocol.py/schema.py — **recommended**) · `jarvis/phone/*`,
`jarvis/heartbeat/{phone,pc}` (transport.py legacy, hardcoded to 2 devices) ·
`chimera/<node>/<action>` (CLAUDE.md aspiration). **Recommendation: standardize on
`jarvis/node/{id}/{verb}`** (proven, structured, retained-aware); optionally rename
the root `jarvis/`→`chimera/` once, mesh-wide.

---

## DELIVERABLE 1 — Hardware Node Architecture

### Node taxonomy (grounded in the existing node model)

| Class | Definition | Transport profile | Examples |
|---|---|---|---|
| **Hub** | Runs Brain + MQTT broker; the only commander | on-bus MQTT client + REST/WS/MCP | **Desktop PC** |
| **Smart node** | Full agent: Python/Termux, MQTT+HMAC, sensors, actuation | `protocol.py` envelope, HMAC-signed, QoS-1 | **Nothing Phone**, **OPPO**, **Vivo**, revived tablet |
| **Constrained node** | MCU, native MQTT, no Python/Tailscale, light/no crypto | reduced payload, LAN/bridge, pre-shared key | **Arduino UNO R4 WiFi**, future ESP32 |
| **Display surface** | No autonomy; rendered to by a host node | driven via a node's `display.*` skill (HDMI/cast) | **TV**, salvaged **LCD** |
| **Peripheral** | Component; only a node when paired with a host | n/a (attached to a host node) | camera, speakers, mic, antenna, battery |

### Per-device verdict

| Device | Becomes a node? | Class | Role | Notes (grounded) |
|---|---|---|---|---|
| **Desktop PC** | Yes | **Hub** | Brain host + Mosquitto broker + Ollama; also a PC **actuator** node (`pc.*` skills) | Brain must get *on the bus* — it currently has no MQTT at all (Phase 2 M2). PC actuation already exists (`bridge_server.py`, `jarvis_core` PC tools). |
| **Nothing Phone 3a Lite** | Yes | **Smart node** | Daily mobile node: voice in/out, `phone.*` skills, sensors | Termux/Ubuntu-proot/Tailscale/SSH already present → run `phone_executor.py` as-is. The reference smart node. |
| **OPPO** | Yes (repurpose) | **Smart node (pinned)** | **Vision/camera node** *or* wall **voice terminal** | Use its built-in camera/mic/speaker rather than salvaged parts. Same Termux agent, single-role skill set. |
| **Vivo 1901** | Yes (repurpose) | **Smart node (pinned)** | **Sensor/monitor node** or second **display** | Ambient sensing (`sensor.*`) or a kiosk display. |
| **Arduino UNO R4 WiFi** | Yes | **Constrained node** | GPIO/sensor/actuator (`gpio.*`, `sensor.*`) | R4 WiFi can run a native MQTT client (PubSubClient). **Tailscale won't run on it** → joins the broker over LAN or via a bridge node (see D5). HMAC-SHA256 is heavy on AVR-class but feasible on the R4 (RA4M1) — use a constrained auth profile. |
| **Television (HDMI)** | Indirectly | **Display surface** | Output for dashboards/video/notifications | A TV is a dumb display: drive it via a host node's `display.show` (HDMI from a node, or cast). Not its own MQTT node unless it's an Android TV. |
| **Salvaged LCD (P101DCA-AB0)** | Eventually | **Display surface** | Jarvis smart-display terminal (CLAUDE.md priority) | Bare panel needs an LVDS/eDP→HDMI **driver board** + a small host (Pi Zero/ESP32-display/old phone). Stretch project. |
| **7000 mAh battery** | n/a | Peripheral | Portable power for a display/voice node | Inspect for swelling first (CLAUDE.md). |
| **Tablet motherboard** | Maybe | (→ Smart node if revived) | Spare Android node | Store intact; revive = another Termux node. |
| **Camera / Speakers / Mic / Antenna** | n/a | Peripheral | Attach to a host SBC/MCU | **Pragmatic call:** the spare phones already *are* camera+mic+speaker+compute — prefer them for vision/voice nodes; keep salvaged parts for the LCD-terminal build + ESP32/RF experiments. |

### Topology

```
                         ┌──────────────────────────────────────┐
                         │  DESKTOP PC  (Hub)                    │
                         │  Brain (cognition, registry, memory)  │
                         │  Mosquitto broker  ·  Ollama          │
                         └───────────────┬──────────────────────┘
                       MQTT v5 over Tailscale (broker bound to tailnet IP)
        ┌──────────────┬─────────────────┼──────────────────┬───────────────┐
        ▼              ▼                  ▼                  ▼               ▼
  Nothing Phone   OPPO (vision)    Vivo (sensors)      PC actuator     LAN bridge
  (smart node)    (smart node)     (smart node)        (on hub)        node (Pi/ESP)
        │              │                                                    │ LAN
   phone.* skills  camera.* skills                                   ┌──────┴──────┐
   voice in/out                                                      ▼             ▼
                                                                  Arduino       ESP32
                                                                  (gpio.*)    (sensor.*)
   display.show ─────────────► TV (HDMI/cast)  /  salvaged LCD terminal
```

---

## DELIVERABLE 2 — Device Registry Design

The registry is the Brain module **missing today** (Phase 2 M3 / Phase 4 Step 2).
It replaces `brain_pc._known_skills` hardcoding and gives the planner ground truth.

**Home:** new Brain module `devices/` (sibling of `identity/`, `goals/`), SQLite-backed
like `goals/store.py`, with an in-memory live view fed by MQTT retained topics.

**Record schema:**
```python
DeviceRecord(
  node_id:        str,            # "nothing-phone", "arduino-1"
  kind:           str,            # hub | smart | constrained | display | peripheral
  platform:       str,            # windows | android-termux | mcu-r4 | esp32
  transport:      str,            # mqtt-hmac | mqtt-native | proxied
  capabilities:   list[str],      # skill names from the node's catalog
  risk_ceiling:   int,            # max Task.risk this node may execute (Phase 2 I5)
  power:          str,            # mains | battery
  reachability:   str,            # tailscale | lan | bridged
  online:         bool,           # derived from presence + heartbeat age
  last_seen:      float,
  meta:           dict,           # battery%, ip, fw version, ...
  registered_at:  float,
)
```

**Population (two sources):**
1. **Static**: known-device config (seed roles/keys).
2. **Dynamic discovery**: subscribe `jarvis/node/+/presence`, `jarvis/node/+/state`,
   `jarvis/skills/catalog/+` (all **retained**) → a node appears the moment it
   connects. Catalog content comes from each node's `SkillRegistry.catalog()`
   (`jarvis/skills.py` already serializes this).

**API (Brain-owned, exposed via REST v2 / MCP):**
`list_nodes()`, `get_node(id)`, `capabilities(skill)` → which online nodes provide
it, `is_online(id)`. The **planner queries this before planning** — only plannable
skills on online nodes within `risk_ceiling` are offered (this is the
`AgentManifest`/dynamic-catalog idea from `BRAIN_V2_DESIGN.md` §5.2, applied to hardware).

---

## DELIVERABLE 3 — MQTT Topic Strategy

Adopt the `protocol.py`/`schema.py` scheme verbatim; extend minimally.

| Topic | Dir | QoS | Retained | Purpose |
|---|---|---|---|---|
| `jarvis/node/{id}/cmd` | Brain → node | 1 | no | Command (skill+params), TTL, id |
| `jarvis/node/{id}/response` | node → Brain | 1 | no | Response (echoes Command.id) |
| `jarvis/node/{id}/event` | node → all | 1 | no | Unsolicited (`battery_low`, sensor trip) |
| `jarvis/node/{id}/presence` | node → all | 1 | **yes** | online/offline (LWT sets offline) |
| `jarvis/node/{id}/state` | node → all | 1 | **yes** | retained snapshot (battery, mode, metrics) |
| `jarvis/node/{id}/heartbeat` | node → all | 0 | no | liveness (20 s; disposable) |
| `jarvis/skills/catalog/{id}` | node → all | 1 | **yes** | retained skill catalog (HAL discovery) |
| `jarvis/broadcast/request` | any → Brain | 1 | no | user utterance intake (`Request`) |

Brain subscribes to the wildcards (`jarvis/node/+/response|event|presence|state`,
`jarvis/skills/catalog/+`); each node subscribes **only** to its own `…/{id}/cmd`.

**Broker policy (Mosquitto on the hub):**
- Bind to the **Tailscale interface**, not `0.0.0.0` (fixes the exposure noted in Phase 3).
- MQTT v5, `session_expiry = 24h`, `keepalive = 60s` (per `protocol.py` constants).
- **Per-node ACLs**: node `X` may publish only `jarvis/node/X/#` + `jarvis/skills/catalog/X`
  and subscribe only `jarvis/node/X/cmd`. Only the Brain principal may publish `…/cmd`.
  This enforces least privilege and kills the "any node can command any node" risk
  (Phase 3) at the broker.
- **Auth tiers by node class**: smart nodes → HMAC envelope (`signing.py`) + broker
  creds; constrained nodes → broker creds + topic ACL (+ optional light HMAC);
  **fail-closed** (reject empty `JARVIS_HMAC_KEY`/token — Phase 3 fix).

---

## DELIVERABLE 4 — Hardware Abstraction Layer Design

**The abstraction is the *skill*, and it already exists** (`jarvis/skills.py`
`Skill`/`SkillRegistry`; `Command.skill`). Brain plans in skills; nodes implement
them for their hardware. Four layers:

```
Brain plan step ─► "display.show" (skill, params)         ① SKILL CONTRACT
        │            name · params_schema · risk · owner     (jarvis/skills.py)
        ▼
Device Registry ─► which ONLINE node provides display.show? ② CAPABILITY ROUTING
        │            (registry.capabilities("display.show"))   (Phase 5 D2)
        ▼
Node SkillRegistry ─► node has registered display.show     ③ NODE CATALOG
        │            (retained catalog topic)                 (pc_skills/phone_skills)
        ▼
Driver ─► termux-api / pyautogui / Firmata-GPIO / HDMI-cast ④ DRIVER (node-internal)
```

**Capability namespacing** (`<class>.<verb>`): `pc.shell.run`, `phone.ring`,
`tts.speak`, `display.show`, `camera.capture`, `gpio.write`, `sensor.read`,
`media.play`. Brain targets a *capability*; the registry resolves the *node*. So
"show this on a display" routes to whatever display node is online (TV-host,
LCD-terminal, or a phone) with **no Brain change**.

- **Smart nodes**: full `SkillRegistry` (the existing `pc_skills.py`/`phone_skills.py`
  are ready-made; `phone_executor.py` is the runner template).
- **Constrained nodes (Arduino/ESP32)**: a tiny fixed skill set (`gpio.*`, `sensor.*`,
  `actuator.set`); the "driver" is firmware. A LAN **bridge node** translates the
  full JSON envelope ↔ a slimmed MCU payload when the MCU can't parse the full schema.
- **Display surfaces**: exposed as a `display.*` skill *on the host node* that owns
  the HDMI/cast link — the TV/LCD themselves never speak MQTT.

This makes hardware **swappable behind capabilities** — the core HAL principle, and
it reuses the skill framework that is currently dead code (`jarvis/`), giving that
investment a purpose.

---

## DELIVERABLE 5 — Future Expansion Strategy

**Adding any node is a 4-step, zero-Brain-code operation:**
1. Install the agent — Termux `phone_executor.py` (smart) or flash firmware (MCU).
2. Node connects → publishes **retained** `presence` + `state` + `skills/catalog`.
3. Brain's Device Registry **auto-discovers** it from those retained topics.
4. Its skills become plannable within its `risk_ceiling`. Done.

**Growth path (aligned to CLAUDE.md roadmap & acquisitions):**
- **ESP32 sensor mesh** (CLAUDE.md acquisition priority): cheapest constrained nodes;
  MQTT-native; ideal first new hardware. Use the LAN-bridge pattern until secured.
- **Vision node** (OPPO): `camera.capture`/`vision.detect` skills → events to Brain.
- **Display nodes** (TV via cast; salvaged LCD terminal): `display.*` skills;
  the LCD-terminal is the CLAUDE.md "Jarvis smart display" stretch build (LCD +
  driver board + small host + salvaged speakers/mic = a voice+display terminal).
- **Audio node**: salvaged speakers + MEMS mic on an SBC → `tts.speak`/`stt.listen`.

**Constrained-node bridge pattern (recommended for Arduino now):**
```
Arduino UNO R4 WiFi ──native MQTT (LAN)──► Bridge node (PC/Pi on tailnet)
                                            translates: full envelope ⇄ MCU JSON,
                                            adds HMAC, enforces risk/ACL on the MCU's behalf
                                          ──► broker (Tailscale)
```
This keeps the tailnet-secured mesh intact while letting non-Tailscale hardware join.

**Standing rules for expansion (so the mesh stays coherent):**
- One topic scheme (`jarvis/node/{id}/{verb}`), one envelope (`protocol.py` merged
  with `schema.py`'s `State`/`Request`/`catalog`), one signing module.
- Every node: presence (LWT) + heartbeat + retained catalog — non-negotiable, so
  discovery and state management are uniform.
- New hardware = new **capability namespace**, never a new Brain branch.

---

## Open hardware constraints (called out honestly)

| Constraint | Impact | Mitigation |
|---|---|---|
| Tailscale can't run on Arduino/ESP32 | MCUs can't join the encrypted tailnet directly | LAN + per-node ACL, or bridge node (D5). |
| Bare LCD / salvaged camera need driver boards + a host | Not nodes on their own | Pair with Pi/ESP32/old phone; or prefer spare phones' built-ins. |
| TV is a dumb display | No autonomy | Drive via a host node's `display.*` (HDMI/cast). |
| HMAC-SHA256 cost on MCUs | Latency/footprint on constrained nodes | Constrained auth profile, or sign at the bridge. |
| Brain has **no MQTT today** | The whole mesh can't reach cognition | Phase 4 Step 1 (put Brain on the bus) is the prerequisite for all of this. |

> Scope reminder: this is a **study**. No firmware, broker config, or Brain
> modules were written; all recommendations reuse existing code patterns and
> remain to be implemented in a later phase.
