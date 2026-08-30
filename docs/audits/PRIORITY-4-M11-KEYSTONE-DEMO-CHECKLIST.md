# Priority #4 M11 — Keystone demo checklist
#
# Session lock-up (2026-08-30): docs/audits/PRIORITY-4-M11-SESSION-LOCKUP.md
# Open breakage: docs/audits/PRIORITY-4-TECH-DEBT.md
#
# Run this when nodes are back online. Tick each box with evidence
# (screenshot, audit row id, or short note). Automated partial checks:
#   GET /api/devices/trial-report
#   python scripts/trial_report.py -o docs/audits/PRIORITY-4-M11-TRIAL-SNAPSHOT.md

## Before you start

- [x] Set trial window: `JARVIS_TRIAL_START_TS=<unix>` in Brain `.env`
- [x] Point Brain at legacy log: `JARVIS_TRIAL_LEGACY_LOG_PATH=C:\Users\Hp\.chimera\legacy_invocations.jsonl`
- [ ] Mosquitto listening on Tailscale IP (`100.73.18.101:1883` anonymous listener)
- [ ] Brain `.env`: `JARVIS_MQTT_HOST=100.73.18.101`, MQTT enabled + HMAC key
- [ ] PC node: `C:\chimera\node-pc.env` with same broker host
- [ ] Phone node: `~/.chimera/node.env` on Nothing Phone (Termux), Tailscale up
- [ ] Start stack: `.\scripts\start_chimera_stack.ps1` (or manual steps below)

### Manual stack (if script fails)

1. Mosquitto service running
2. Brain API: `python main.py api` from Brain repo (venv) — or `.\scripts\start_chimera_stack.ps1`
3. Dashboard: serve `frontend/dashboard` on :5173 (or open via Brain if wired)
4. PC node: `python run_chimera_node.py` with `C:\chimera\node-pc.env`
5. Phone node: `python run_chimera_node.py` with phone env

---

## §3.5 Flow — one recorded round-trip per class

| # | Command class | Example utterance / invoke | Spine ok | Audit id / note |
|---|---------------|----------------------------|----------|-----------------|
| 1 | `phone.battery` | "what's my phone battery" | [x] | audit `4591c091` + NL query 2026-08-30 |
| 2 | `phone.whatsapp.send` | whatsapp to contact (test number) | [x] | audit `0ebeab99` open-only (`auto_send:false`); auto-send blocked — adb not paired (TD-P4-01) |
| 3 | `phone.sms.send` | sms to test number | [x] | audit `cc3489ad` |
| 4 | `phone.app.open` | "open Settings on my phone" | [x] | audit `cd52159c` |
| 5 | `phone.notify` or `phone.tts` | notify or TTS demo | [x] | audit `709003f9` notify, `1c4ef913` tts |
| 6 | `pc.system.lock` | "lock my computer" | [x] | audit `e8ef4945` |
| 7 | `pc.media.control` | "volume up" / play_pause | [x] | audit `0f976f44` |

- [x] **C7 concurrency:** two pings in flight to PC node — both `responded` (audit `1a76a411`, `c4da0a8e`)
- [ ] **C9 live declarations:** remove a skill from node declaration; confirm Brain no longer plans it (no code change)
- [x] **C10 approval gate:** `pc.shell.run` → `approval_required` (`92a35b27`); approve once → dispatch; replay → 404 already used
- [ ] **C11 kernel ceiling:** Brain-authorized command refused by node kernel when ceiling forbids it

---

## §3.6(2) Outcome evidence (trial window — not one session)

Record in this file or trial report when evidenced:

- [ ] **(a) Adoption:** `trial-report` shows `legacy_zero_for_covered: true` for entire window
- [ ] **(b) Reliability:** every failure root-caused; no recurring failure class after fix
- [ ] **(c) Real conditions:**
  - [ ] Multiple phone sleep/wake (Doze) cycles during trial
  - [ ] At least one broker or node restart/reconnect mid-trial
  - [ ] Multi-day continuous node uptime (heartbeat log)

---

## §3.7 Failure checks (must NOT occur)

- [ ] No planning originating on a node
- [ ] No high-tier execute without distinct-principal single-use approval
- [ ] No kernel accepting ceiling change from Brain message
- [ ] No revert to legacy stack for covered classes during trial

---

## When complete

- Export snapshot: `python scripts/trial_report.py -o docs/audits/PRIORITY-4-M11-TRIAL-SNAPSHOT.md`
- Proceed to M12 only after maintainer closes trial with evidence (ADR-014 review)
