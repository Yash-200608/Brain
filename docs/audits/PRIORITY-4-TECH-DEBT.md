# Priority #4 — Technical debt register (living)

> **Started:** 2026-08-30 · **Scope:** Demo blockers and known-broken behavior
> discovered during M11 spine bring-up. Severity = impact on the keystone trial.
> Update this file when something is fixed (move to "Resolved" with date) or new
> breakage is found.

For pre-P4 architectural debt see `docs/PHASE3_TECH_DEBT_AUDIT.md`. For P4
milestone obligations see `docs/PRIORITY-4_DEFINITION.md` §7.

---

## Open — not working / blocked

| ID | Severity | Item | Repo | Symptom | Unblock / fix |
|----|----------|------|------|---------|----------------|
| TD-P4-01 | **High** | **WhatsApp auto-send** | JARVIS | `phone.whatsapp.send` opens WhatsApp but message not typed and Send not tapped; error: *"auto-send needs Wireless Debugging + adb connect"* or *"Send could not be tapped"* | On phone: enable **Wireless debugging**, run `scripts/setup_whatsapp_adb.sh`, verify `adb devices` shows a device. Android blocks `input tap`/`input text` from Termux uid (`INJECT_EVENTS`); adb shell is required. |
| TD-P4-02 | **High** | **WhatsApp message pre-fill unreliable** | JARVIS | User reports composer opens **empty** even when intent returns ok | Depends on TD-P4-01 path: skill now types via adb after open. Without adb, jid SEND / wa.me pre-fill is inconsistent across WhatsApp versions. |
| TD-P4-03 | **Medium** | **`phone.location`** | JARVIS | Skill fails — Termux location permission not granted | Android Settings → Apps → Termux → Permissions → Location; retry `termux-location`. |
| TD-P4-04 | **Medium** | **Contact name lookup** | JARVIS | SMS/WhatsApp by name may fail silently if permission missing | Grant Termux **Contacts** permission; requires `termux-contact-list` (Termux:API). |
| TD-P4-05 | **Medium** | **Duplicate Brain/PC processes** | Brain / ops | Random **504** on invoke; wrong handler consumes MQTT reply | Always use `scripts/stop_chimera_stack.ps1` then `start_chimera_stack.ps1`; do not run second Brain via Cursor/uv on same broker key. |
| TD-P4-06 | **Medium** | **Phone node not persistent** | JARVIS / ops | `run_chimera_node.py` dies; dashboard shows phone offline until manual restart | Register **termux-services** (runit) for `run_chimera_proot.sh`; or watchdog script. Not implemented. |
| TD-P4-07 | **Medium** | **M11 trial not started** | Brain | No outcome evidence; `JARVIS_TRIAL_START_TS` unset | Set env in Brain `.env`, configure legacy log path, run checklist §3.5–3.6. |
| TD-P4-08 | **Medium** | **Keystone command classes incomplete** | Brain | Trial snapshot: `phone.whatsapp.send`, `phone.sms.send`, `phone.app.open`, `phone.tts` show 0 spine-ok in window | Complete checklist invokes with audit ids after fixing TD-P4-01–04. |
| TD-P4-09 | **Low** | **Uncommitted session work** | Both | Fixes exist only locally + SCP to phone; not on git remote | Commit/push JARVIS `phone_skills.py`, tests, `setup_whatsapp_adb.sh`; Brain dashboard, intents, policy. |
| TD-P4-10 | **Low** | **Dashboard manual API key** | Brain | Operator must paste Bearer token in browser localStorage | Acceptable for demo; document key in operator runbook (not in repo). |
| TD-P4-11 | **Low** | **M11 checklist stale commands** | Brain | Checklist says `uvicorn main:app`; correct entry is `python main.py api` | Update checklist when next editing that file. |
| TD-P4-12 | **Low** | **WhatsApp UI automation fragility** | JARVIS | Send-button tap uses uiautomator + coordinate fallback; breaks on WA UI updates | Monitor after TD-P4-01; consider accessibility service only if adb proves insufficient. |

---

## Open — design / ops (not broken, but debt)

| ID | Severity | Item | Notes |
|----|----------|------|-------|
| TD-P4-20 | Medium | MQTT TLS + broker ACLs | Tailscale is current boundary; see PHASE3 item 14. |
| TD-P4-21 | Medium | No termux-service for phone node | Documented in M9; not done. |
| TD-P4-22 | Low | `phone.whatsapp.send` cannot truly silent-send | Android/WhatsApp policy; auto-send = tap Send via adb, not background send. |
| TD-P4-23 | Low | SMS as fallback for guaranteed auto-delivery | `phone.sms.send` works without adb; document in dashboard skill hints. |

---

## Resolved this session

| ID | Resolved | Item | Fix |
|----|----------|------|-----|
| TD-P4-R1 | 2026-08-30 | `phone.app.open` false success from proot | `termux_android_runner` + native Termux `am start --user 0`; stricter `_launch_ok()` |
| TD-P4-R2 | 2026-08-30 | PC node declared all 13 skills | `CHIMERA_SKILL_SET=pc\|phone` + dispatcher platform preference |
| TD-P4-R3 | 2026-08-30 | `phone.tts` HTTP 504 | Brain `skill_dispatch_timeout` 65s for `phone.tts` |
| TD-P4-R4 | 2026-08-30 | Dashboard invoke always green | Show red when `result.ok === false`; human-readable messaging text |
| TD-P4-R5 | 2026-08-30 | Duplicate contact names (Gmail sync) | Dedupe by normalized phone digits; `index` param for real ambiguities |
| TD-P4-R6 | 2026-08-30 | SMS/WhatsApp number-only | `recipient` / `name` / `phone` params + `termux-contact-list` lookup |
| TD-P4-R7 | 2026-08-30 | `input`/`wm` not found from runner | `ANDROID_SYSTEM_BIN` in Termux bash PATH (still blocked by INJECT_EVENTS without adb) |

---

## How to add entries

```markdown
| TD-P4-XX | Severity | Short title | Repo | Symptom | Unblock / fix |
```

Increment ID; link from session lock-up if milestone-sized.
