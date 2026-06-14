import pytest
from pydantic import ValidationError

from protocols import PROTOCOL_VERSION, EnvelopeType, make_envelope, parse_envelope


def test_envelope_defaults():
    env = make_envelope(EnvelopeType.TURN_COMPLETED, session="s1", payload={"response": "hi"})
    assert env.version == PROTOCOL_VERSION
    assert env.type == "turn.completed"
    assert env.session == "s1"
    assert env.sequence == 0
    assert env.timestamp > 0
    assert env.payload == {"response": "hi"}


def test_envelope_round_trip():
    env = make_envelope(EnvelopeType.TASK_PROGRESS, session="s2", sequence=7, payload={"pct": 50})
    again = parse_envelope(env.to_dict())
    assert again == env


def test_envelope_ignores_unknown_fields():
    data = {"version": 2, "type": "turn.token", "future_field": "ignored", "payload": {}}
    env = parse_envelope(data)
    assert env.type == "turn.token"
    assert not hasattr(env, "future_field")


def test_envelope_requires_type():
    with pytest.raises(ValidationError):
        parse_envelope({"version": 2, "payload": {}})
    with pytest.raises(ValidationError):
        parse_envelope({"version": 2, "type": "", "payload": {}})
