"""Priority #4 Milestone 7 -- the Brain-side skill risk policy and the
deterministic device-intent mapper.
"""

from __future__ import annotations

from core.device_intents import map_device_intent
from devices.policy import skill_dispatch_timeout, skill_risk_int


# ---------------------------------------------------------------------- #
# Policy                                                                   #
# ---------------------------------------------------------------------- #


def test_known_tiers() -> None:
    assert skill_risk_int("ping") == 0
    assert skill_risk_int("phone.battery") == 0
    assert skill_risk_int("phone.whatsapp.send") == 1
    assert skill_risk_int("pc.system.lock") == 1
    assert skill_risk_int("pc.shell.run") == 2


def test_unknown_skill_fails_closed_to_approval_required() -> None:
    assert skill_risk_int("mystery.future.skill") == 2


def test_dangerous_keywords_fail_closed() -> None:
    assert skill_risk_int("pc.files.delete") == 2
    assert skill_risk_int("node.shutdown.now") == 2


def test_dispatch_timeout_covers_slow_phone_skills() -> None:
    assert skill_dispatch_timeout("phone.battery") == 15.0
    assert skill_dispatch_timeout("phone.tts") == 65.0
    assert skill_dispatch_timeout("phone.location") == 35.0


# ---------------------------------------------------------------------- #
# Mapper -- the confirmed keystone command classes                         #
# ---------------------------------------------------------------------- #


def test_battery_phrasings() -> None:
    for text in ("what's my battery", "phone dying?", "juice left?"):
        intent = map_device_intent(text)
        assert intent is not None, text
        assert intent.skill == "phone.battery"
        assert intent.risk == 0


def test_whatsapp_send_extracts_recipient_and_message() -> None:
    intent = map_device_intent("send a whatsapp to Mom that I'm running late")
    assert intent is not None
    assert intent.skill == "phone.whatsapp.send"
    assert intent.params["phone"] == "Mom"
    assert "running late" in intent.params["message"]
    assert intent.risk == 1


def test_whatsapp_without_extractable_recipient_falls_through_to_llm() -> None:
    assert map_device_intent("send a whatsapp sometime maybe") is None


def test_sms_send() -> None:
    intent = map_device_intent("send an sms to +911234 that on my way")
    assert intent is not None
    assert intent.skill == "phone.sms.send"
    assert intent.params["phone"] == "+911234"


def test_open_app_on_phone() -> None:
    intent = map_device_intent("open spotify on my phone")
    assert intent is not None
    assert intent.skill == "phone.app.open"
    assert intent.params == {"app": "spotify"}


def test_lock_pc() -> None:
    intent = map_device_intent("lock my computer")
    assert intent is not None
    assert intent.skill == "pc.system.lock"
    assert intent.risk == 1


def test_volume_and_media() -> None:
    assert map_device_intent("volume up").params == {"command": "volume_up"}
    assert map_device_intent("quiet down").params == {"command": "volume_down"}
    assert map_device_intent("pause that song").params == {"command": "play_pause"}


def test_tts_quoted() -> None:
    intent = map_device_intent('say "dinner is ready"')
    assert intent is not None
    assert intent.skill == "phone.tts"
    assert intent.params == {"text": "dinner is ready"}


def test_shell_is_always_risk_2() -> None:
    intent = map_device_intent("run shell: whoami")
    assert intent is not None
    assert intent.skill == "pc.shell.run"
    assert intent.params == {"command": "whoami"}
    assert intent.risk == 2


def test_chitchat_falls_through() -> None:
    for text in ("hello", "what can you do", "tell me about the roman empire", ""):
        assert map_device_intent(text) is None, text
