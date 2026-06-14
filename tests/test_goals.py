import tempfile

from goals.models import Goal, Subtask, GoalStatus
from goals.store import GoalStore


def test_goal_lifecycle():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = f.name
    store = GoalStore(db_path=db)
    g = Goal(description="ship V1", subtasks=[Subtask(text="write tests"), Subtask(text="merge")])
    store.upsert(g)
    assert store.complete_subtask(g.id, "write tests")
    refreshed = store.get(g.id)
    assert any(s.done and s.text == "write tests" for s in refreshed.subtasks)
    assert refreshed.status == GoalStatus.ACTIVE


def test_complete_from_instruction():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = f.name
    store = GoalStore(db_path=db)
    g = Goal(description="x", subtasks=[Subtask(text="alpha")])
    store.upsert(g)
    instr = f'COMPLETE_SUBTASK goal_id="{g.id}" subtask="alpha"'
    assert store.complete_subtask_from_instruction(instr)


def test_complete_subtask_no_match_returns_false():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = f.name
    store = GoalStore(db_path=db)
    g = Goal(description="x", subtasks=[Subtask(text="alpha")])
    store.upsert(g)
    assert not store.complete_subtask(g.id, "does-not-exist")
    assert not store.complete_subtask("missing-goal", "alpha")


def test_goal_completes_when_all_subtasks_done():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = f.name
    store = GoalStore(db_path=db)
    g = Goal(description="x", subtasks=[Subtask(text="alpha"), Subtask(text="beta")])
    store.upsert(g)
    assert store.complete_subtask(g.id, "alpha")
    assert store.complete_subtask(g.id, "beta")
    assert store.get(g.id).status == GoalStatus.COMPLETE
