from agents.planner import PlannerAgent


def test_planner_parses_valid_json():
    p = PlannerAgent()
    raw = '[{"agent":"executor","instruction":"hi","risk":0}]'
    steps = p._parse(raw)
    assert len(steps) == 1
    assert steps[0]["agent"] == "executor"


def test_planner_rejects_bad_step():
    p = PlannerAgent()
    raw = '[{"agent":"foo","instruction":"x","risk":0}]'
    assert p._parse(raw) == []
