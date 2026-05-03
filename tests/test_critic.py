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
