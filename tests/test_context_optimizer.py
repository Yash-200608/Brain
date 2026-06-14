from orchestrator.context_optimizer import ContextOptimizer


def test_build_formats_and_indexes_chunks():
    opt = ContextOptimizer()
    out = opt.build([{"text": "alpha"}, {"text": "beta"}])
    assert "[0] alpha" in out
    assert "[1] beta" in out


def test_build_respects_max_chars():
    opt = ContextOptimizer(max_chars=20)
    out = opt.build([{"text": "x" * 15}, {"text": "y" * 15}])
    assert "y" not in out
    assert len(out) <= 20


def test_build_empty_input():
    assert ContextOptimizer().build([]) == ""
