"""Confirmed command classes for the Priority #4 keystone demo (§3.6 item 1).

These are the daily-use classes the retirement trial measures against.
Spine-side coverage is read from dispatch_audit; legacy-side adoption is
read from the JSONL log written by JARVIS's legacy_invocation_log module.
"""

from __future__ import annotations

# Canonical demo list from PRIORITY-4_DEFINITION.md §3.6(1).
CONFIRMED_COMMAND_CLASSES: tuple[str, ...] = (
    "phone.battery",
    "phone.whatsapp.send",
    "phone.sms.send",
    "phone.app.open",
    "phone.notify",
    "phone.tts",
    "pc.system.lock",
    "pc.media.control",
)

# phone.notify and phone.tts share one adoption slot — either satisfies
# the "notify or tts" demo line item.
NOTIFY_OR_TTS: frozenset[str] = frozenset({"phone.notify", "phone.tts"})


def normalize_skill(skill: str) -> str:
    """Map spine skill names onto confirmed classes where applicable."""
    s = skill.strip()
    if s == "pc.volume.set":
        return "pc.media.control"
    return s


def notify_or_tts_covered(classes_with_spine_success: set[str]) -> bool:
    return bool(classes_with_spine_success & NOTIFY_OR_TTS)
