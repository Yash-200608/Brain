import time

import pytest
from pydantic import ValidationError

from protocols import CONTRACT_VERSION, ChimeraEnvelope, RiskTier, sign, verify

KEY = "f" * 64


def _envelope(**overrides) -> ChimeraEnvelope:
    fields = {"node": "pc-main", "verb": "cmd", "action": "get_battery"}
    fields.update(overrides)
    return ChimeraEnvelope(**fields)


def test_sign_verify_round_trip():
    env = sign(_envelope(), KEY)
    assert env.sig
    assert verify(env, KEY) is True


def test_unsigned_envelope_fails_verification():
    env = _envelope()
    assert env.sig == ""
    assert verify(env, KEY) is False


def test_tampered_action_rejected():
    env = sign(_envelope(), KEY)
    tampered = env.model_copy(update={"action": "wipe_disk"})
    assert verify(tampered, KEY) is False


def test_tampered_risk_rejected():
    env = sign(_envelope(risk=RiskTier.LOW), KEY)
    tampered = env.model_copy(update={"risk": RiskTier.HIGH})
    assert verify(tampered, KEY) is False


def test_expired_timestamp_rejected():
    env = sign(_envelope(), KEY)
    stale = env.model_copy(update={"ts": int(time.time()) - 121})
    # Re-sign over the stale ts so the HMAC matches -- only the skew check
    # should reject this, not a signature mismatch.
    resigned = sign(stale.model_copy(update={"sig": ""}), KEY)
    assert verify(resigned, KEY) is False


def test_wrong_key_rejected():
    env = sign(_envelope(), KEY)
    assert verify(env, "0" * 64) is False


def test_sign_requires_nonempty_key():
    with pytest.raises(ValueError):
        sign(_envelope(), "")


def test_default_risk_is_fail_closed_high():
    assert _envelope().risk == RiskTier.HIGH


def test_extra_field_rejected():
    """Deliberate divergence from protocols.envelope.Envelope's
    extra="ignore" -- a signed contract must reject unknown fields rather
    than silently accept unvalidated data past validation."""
    with pytest.raises(ValidationError):
        ChimeraEnvelope(node="pc-main", verb="cmd", smuggled_field="evil")


def test_contract_version_default():
    assert _envelope().version == CONTRACT_VERSION


class TestRiskTierFailClosed:
    def test_from_value_unknown_string_is_high(self):
        assert RiskTier.from_value("catastrophic") is RiskTier.HIGH

    def test_from_value_non_string_is_high(self):
        assert RiskTier.from_value(None) is RiskTier.HIGH
        assert RiskTier.from_value(42) is RiskTier.HIGH

    def test_from_value_known_strings_case_insensitive(self):
        assert RiskTier.from_value("low") is RiskTier.LOW
        assert RiskTier.from_value("MEDIUM") is RiskTier.MEDIUM
        assert RiskTier.from_value("High") is RiskTier.HIGH

    def test_from_value_passthrough(self):
        assert RiskTier.from_value(RiskTier.LOW) is RiskTier.LOW

    @pytest.mark.parametrize(
        "legacy,expected",
        [(0, RiskTier.LOW), (1, RiskTier.MEDIUM), (2, RiskTier.HIGH), (99, RiskTier.HIGH), (-1, RiskTier.LOW)],
    )
    def test_from_legacy_int(self, legacy, expected):
        assert RiskTier.from_legacy_int(legacy) is expected

    def test_to_legacy_int_round_trip(self):
        for tier in RiskTier:
            assert RiskTier.from_legacy_int(tier.to_legacy_int()) is tier
