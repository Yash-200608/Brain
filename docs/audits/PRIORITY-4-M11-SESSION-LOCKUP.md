# Priority #4 M11 — Session lock-up

> **Date:** 2026-08-30 (local) · **Scope:** Brain + JARVIS spine demo prep through
> phone messaging / app-open debugging. This document freezes progress *as of this
> session* and points at open technical debt. It does not replace the keystone
> checklist or trial snapshot — it summarizes them.

---

## 1. Architecture locked for Phase 1

Accepted and in progress (no redesign):

- **One Brain** (cognition, memory, dispatch, audit) + **one JARVIS platform**
  (nodes, SDK, skills) + **many nodes** over MQTT/Tailscale.
- Brain plans and invokes; nodes execute; MQTT + HMAC spine; Jarvis stays
  lightweight.

---

## 2. Infrastructure baseline (last verified ~2026-08-30)

| Component | Target | Notes |
|-----------|--------|--------|
| Mosquitto | `100.73.18.101:1883` | Tailscale broker |
| Brain API | `:8000` | Use `python main.py api` (Brain venv), not bare `uvicorn main:app` |
| Dashboard | `:5173` | `frontend/dashboard` |
| PC node | `jarvis-core-pc` | `CHIMERA_SKILL_SET=pc`, env `C:\chimera\node-pc.env` |
| Phone node | `nothing-phone-3a` | proot via `scripts/run_chimera_proot.sh`, env `~/.chimera/node.env` |
| Phone SSH | `u0_a293@100.86.19.9:8022` | Tailscale |

**Ops scripts (Brain repo):**

- `scripts/start_chimera_stack.ps1` — starts stack, kills duplicate Brain/PC first
- `scripts/stop_chimera_stack.ps1` — clean shutdown

**Recurring ops issue:** duplicate Brain or PC Python processes (Brain venv + stray
`uv`/Cursor copies) break MQTT response correlation → random **504** timeouts.
Mitigation: stop stack script, then start stack script.

**Phone node stability:** process drops offline after restarts; requires manual
`nohup bash scripts/run_chimera_proot.sh` or termux-service (not automated yet).

---

## 3. Code landed (committed vs local)

### JARVIS — on `origin/main`

| Commit | Summary |
|--------|---------|
| `bf19e06` | Contact-aware messaging, WhatsApp adb automation, SMS/WhatsApp clean responses |
| `2e4b6fa` | Per-node skill profiles (`CHIMERA_SKILL_SET=pc\|phone\|all`) |
| `49cb9ca` | `phone.app.open` proot fix — native Termux `am`, `Starting: Intent` detection |

### Brain — on `origin/main`

| Commit | Summary |
|--------|---------|
| `a928e59` | Trial env settings fix + `scripts/m11_spine_smoke.py` |
| `143724a` | Phone messaging UX, M11 session lock-up + tech debt docs |
| `112d0ae` | M11 trial instrumentation, dispatcher routing, audit/trial-report |
| `3f4f5e8` / `7acb632` | Stack start/stop scripts, dedupe on start |

---

## 4. Command status (manual session testing)

| Skill | Status | Evidence |
|-------|--------|----------|
| `ping` | **Working** | PC + phone |
| `phone.battery` | **Working** | termux-battery-status |
| `phone.tts` | **Working** | after dispatch timeout fix (65s) |
| `phone.notify` / `phone.vibrate` / `phone.ring` / `phone.torch` | **Working** | termux-api |
| `phone.sms.send` | **Working** (number); **unverified** (contact name) | `termux-sms-send`; needs Contacts permission for names |
| `pc.media.control` / `pc.system.lock` / `pc.shell.run` | **Working** | approval gate on shell |
| NL battery / volume / lock | **Working** | deterministic intent mapper |
| `phone.app.open` | **Partial** | Opens via native Termux `am`; verified settings intent on device |
| `phone.whatsapp.send` | **Partial** | Opens + manual send (`auto_send:false`); auto-send blocked until adb paired |
| `phone.location` | **Not working** | Termux location permission not granted |
| M11 trial window | **Started** | `JARVIS_TRIAL_START_TS` set in `.env`; Brain restarted 2026-08-30 |
| M11 keystone checklist | **§3.5 + C7/C10 done** | C9/C11 + §3.6 multi-day evidence remain |

Latest automated trial snapshot (`PRIORITY-4-M11-TRIAL-SNAPSHOT.md`): 28 audit events,
17 responded / 11 timeout; several command classes show 0 spine-ok rows for the trial
window (whatsapp, sms, app.open).

---

## 5. M11 checklist progress (summary)

See `docs/audits/PRIORITY-4-M11-KEYSTONE-DEMO-CHECKLIST.md` for full rows.

- [x] Stack can be brought up (manual + scripts)
- [x] Phone node reachable via SSH/proot
- [x] Partial spine invoke / NL query exercised
- [x] Trial window env vars configured
- [x] All §3.5 command classes recorded with audit evidence (WhatsApp auto-send excepted — TD-P4-01)
- [x] C7 concurrency
- [x] C10 approval gate (shell dispatch result ok=false — investigate separately)
- [ ] C9 live declarations, C11 kernel ceiling
- [ ] §3.6 outcome evidence (multi-day, Doze, broker restart)

**M12 / ADR-014 review:** not started — blocked on successful trial.

---

## 6. Technical debt register

Full living list: **`docs/audits/PRIORITY-4-TECH-DEBT.md`** (created this session).

Items that are **not working** or **blocked** are tracked there with severity,
owner repo, and unblock steps. Phase 3 debt (`PHASE3_TECH_DEBT_AUDIT.md`) remains
valid for historical/architectural items; P4 register is for *current demo blockers*.

---

## 7. Recommended next session (ordered)

1. **Phone:** run `bash ~/Jarvis-2.0/scripts/setup_whatsapp_adb.sh` (Wireless
   Debugging ON) — unblocks WhatsApp auto-send (TD-P4-01).
2. **Termux:** grant Contacts (name lookup) and Location (`phone.location`).
3. **M11:** C9 live declarations + C11 kernel ceiling demos; export trial snapshot.
4. **Phone node:** register termux-service so `run_chimera_proot.sh` survives sleep (TD-P4-06).
5. **Fix:** `scripts/trial_report.py` CLI reads empty audit when run offline — use
   `GET /api/devices/trial-report` or point CLI at live `devices.db`.

---

## 8. References

- Keystone checklist: `docs/audits/PRIORITY-4-M11-KEYSTONE-DEMO-CHECKLIST.md`
- Trial snapshot: `docs/audits/PRIORITY-4-M11-TRIAL-SNAPSHOT.md`
- P4 definition: `docs/PRIORITY-4_DEFINITION.md`
- Phase 3 debt (historical): `docs/PHASE3_TECH_DEBT_AUDIT.md`
- P4 open debt: `docs/audits/PRIORITY-4-TECH-DEBT.md`
