from orchestrator.planner import Planner


def test_risk_floor_flags_dangerous_tokens():
    assert Planner._risk_floor("please rm -rf the directory") == 1
    assert Planner._risk_floor("delete the user table") == 1
    assert Planner._risk_floor("use subprocess to launch it") == 1


def test_risk_floor_zero_for_safe_text():
    assert Planner._risk_floor("summarise the meeting notes") == 0
    assert Planner._risk_floor("") == 0
