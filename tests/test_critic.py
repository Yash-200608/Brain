from agents.critic import CriticAgent


def test_critic_parses_ok():
    c = CriticAgent()
    parsed = c._parse('{"confidence": 0.9, "verdict": "ok", "reason": "fine"}')
    assert parsed["verdict"] == "ok"
    assert parsed["confidence"] == 0.9


def test_critic_handles_bad_json():
    c = CriticAgent()
    parsed = c._parse("totally not json")
    assert "verdict" in parsed


def test_critic_coerces_non_numeric_confidence():
    c = CriticAgent()
    parsed = c._parse('{"confidence": "high", "verdict": "ok", "reason": "x"}')
    assert parsed["confidence"] == 0.5


def test_critic_clamps_out_of_range_confidence():
    c = CriticAgent()
    parsed = c._parse('{"confidence": 3.5, "verdict": "ok", "reason": "x"}')
    assert parsed["confidence"] == 1.0


def test_critic_normalises_unknown_verdict():
    c = CriticAgent()
    parsed = c._parse('{"confidence": 0.9, "verdict": "banana", "reason": "x"}')
    assert parsed["verdict"] == "ok"
