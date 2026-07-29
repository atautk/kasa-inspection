from modules.core.decision_engine import DecisionEngine


def test_default_threshold_is_3_percent():

    engine = DecisionEngine()

    assert engine.change_threshold == 3.0


def test_ratio_at_or_above_threshold_is_full():

    engine = DecisionEngine()

    assert engine.detect({"change_ratio": 3.0}) == "FULL"
    assert engine.detect({"change_ratio": 10.0}) == "FULL"


def test_ratio_below_threshold_is_empty():

    engine = DecisionEngine()

    assert engine.detect({"change_ratio": 2.9}) == "EMPTY"
    assert engine.detect({"change_ratio": 0.0}) == "EMPTY"


def test_missing_change_ratio_defaults_to_empty():

    engine = DecisionEngine()

    assert engine.detect({}) == "EMPTY"


def test_set_threshold_changes_behavior():

    engine = DecisionEngine()
    engine.set_threshold(10)

    assert engine.detect({"change_ratio": 5.0}) == "EMPTY"
    assert engine.detect({"change_ratio": 10.0}) == "FULL"


def test_set_threshold_accepts_string_like_values():

    engine = DecisionEngine()
    engine.set_threshold("7.5")

    assert engine.change_threshold == 7.5
