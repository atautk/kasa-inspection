import json

import pytest

from modules.configuration.band import Band
from modules.configuration.inspection_logger import InspectionLogger


@pytest.fixture
def band(tmp_path):

    return Band(
        id="test_band",
        name="Test Band",
        root=tmp_path,
        reference=tmp_path / "reference.png",
        roi=tmp_path / "roi.json",
        models=tmp_path / "models"
    )


@pytest.fixture
def logger(band):

    return InspectionLogger(band)


def make_result(ok):

    return {
        "G01": {
            "state": "FULL",
            "expected": "FULL" if ok else "EMPTY",
            "ok": ok,
            "change_ratio": 1.0,
            "changed_pixels": 1
        }
    }


def test_first_result_is_always_logged(logger):

    assert logger.log_if_changed(make_result(True), "clio") is True


def test_repeated_same_result_is_not_logged_again(logger):

    logger.log_if_changed(make_result(True), "clio")

    assert logger.log_if_changed(make_result(True), "clio") is False


def test_ok_to_ng_transition_is_logged(logger):

    logger.log_if_changed(make_result(True), "clio")

    assert logger.log_if_changed(make_result(False), "clio") is True


def test_empty_results_are_never_logged(logger):

    assert logger.log_if_changed({}, "clio") is False


def test_fetch_recent_returns_most_recent_first(logger):

    logger.log_if_changed(make_result(True), "clio")
    logger.log_if_changed(make_result(False), "clio")

    rows = logger.fetch_recent()

    assert [row["overall_result"] for row in rows] == ["NG", "OK"]


def test_mark_reviewed_ok_preserves_original_result(logger):

    logger.log_if_changed(make_result(False), "clio")
    record_id = logger.fetch_recent()[0]["id"]

    logger.mark_reviewed_ok(record_id)

    row = logger.fetch_recent()[0]

    assert row["overall_result"] == "OK"
    assert row["reviewed"] == 1
    assert row["original_result"] == "NG"


def test_mark_reviewed_ok_is_idempotent_on_original_result(logger):

    logger.log_if_changed(make_result(False), "clio")
    record_id = logger.fetch_recent()[0]["id"]

    logger.mark_reviewed_ok(record_id)
    logger.mark_reviewed_ok(record_id)

    row = logger.fetch_recent()[0]

    assert row["original_result"] == "NG"


def test_mark_reviewed_ok_unknown_id_returns_false(logger):

    assert logger.mark_reviewed_ok(999) is False


def test_correct_roi_recomputes_overall_result(logger):

    results = {
        "G01": {
            "state": "EMPTY", "expected": "FULL",
            "ok": False, "change_ratio": 1.0, "changed_pixels": 1
        },
        "G02": {
            "state": "EMPTY", "expected": "FULL",
            "ok": False, "change_ratio": 1.0, "changed_pixels": 1
        }
    }

    logger.log_if_changed(results, "clio")
    record_id = logger.fetch_recent()[0]["id"]

    logger.correct_roi(record_id, "G01", True)

    row = logger.fetch_recent()[0]
    roi_results = json.loads(row["roi_results"])

    assert row["overall_result"] == "NG"
    assert roi_results["G01"]["ok"] is True
    assert roi_results["G01"]["original_ok"] is False

    logger.correct_roi(record_id, "G02", True)

    row = logger.fetch_recent()[0]

    assert row["overall_result"] == "OK"


def test_correct_roi_unknown_roi_returns_false(logger):

    logger.log_if_changed(make_result(False), "clio")
    record_id = logger.fetch_recent()[0]["id"]

    assert logger.correct_roi(record_id, "DOES_NOT_EXIST", True) is False


def test_compute_stats_counts_ok_and_ng_correctly(logger):

    logger.log_if_changed(make_result(True), "clio")
    logger.log_if_changed(make_result(False), "clio")
    logger.log_if_changed(make_result(True), "clio")

    stats = logger.compute_stats()

    assert stats["total"] == 3
    assert stats["ok_count"] == 2
    assert stats["ng_count"] == 1
    assert stats["by_roi"]["G01"] == {"ok": 2, "ng": 1}


def test_clear_removes_all_records_and_resets_state(logger):

    logger.log_if_changed(make_result(True), "clio")

    logger.clear()

    assert logger.fetch_recent() == []
    assert logger.last_overall_result is None
