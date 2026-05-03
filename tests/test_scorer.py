from reflection.scorer import ImportanceScorer


def test_scorer_high_keywords():
    s = ImportanceScorer()
    assert s.score("Always remember the deadline") > 0.7


def test_scorer_low_keywords():
    s = ImportanceScorer()
    assert s.score("maybe a joke about that") < 0.5
