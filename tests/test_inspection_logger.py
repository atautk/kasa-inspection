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


def test_ok_to_ng_transition_is_logged_after_confirmation(logger):

    logger.log_if_changed(make_result(True), "clio")

    # tek karelik bir NG, kamera titremesi olabilir - hemen loglanmamalı
    assert logger.log_if_changed(make_result(False), "clio") is False
    assert logger.log_if_changed(make_result(False), "clio") is False

    # CONFIRM_FRAMES'e ulaşınca (ardışık aynı yeni durum) loglanmalı
    assert logger.log_if_changed(make_result(False), "clio") is True


def test_single_frame_flicker_does_not_trigger_logging():
    """
    Regresyon testi: kamera oynadığı için tek bir karede OK<->NG
    yanlışlıkla değişip hemen eski durumuna dönerse, aynı fiziksel
    kasa için birden fazla loglama/bildirim tetiklenmemeli.
    """

    from modules.configuration.band import Band
    import tempfile
    from pathlib import Path

    root = Path(tempfile.mkdtemp())
    band = Band(
        id="test_band", name="Test Band", root=root,
        reference=root / "reference.png", roi=root / "roi.json",
        models=root / "models"
    )
    logger = InspectionLogger(band)

    logger.log_if_changed(make_result(True), "clio")

    # kamera titremesi: bir kare NG, hemen ardından tekrar OK
    assert logger.log_if_changed(make_result(False), "clio") is False
    assert logger.log_if_changed(make_result(True), "clio") is False

    stats = logger.compute_stats()
    assert stats["total"] == 1
    assert stats["ok_count"] == 1
    assert stats["ng_count"] == 0


def test_intermittent_flicker_resets_confirmation_streak():
    """
    Ardışık olmayan (OK ile bölünmüş) NG kareleri doğrulama sayacını
    sıfırlamalı - sadece KESİNTİSİZ CONFIRM_FRAMES kadar aynı sonuç
    gerçek bir geçiş sayılmalı.
    """

    from modules.configuration.band import Band
    import tempfile
    from pathlib import Path

    root = Path(tempfile.mkdtemp())
    band = Band(
        id="test_band", name="Test Band", root=root,
        reference=root / "reference.png", roi=root / "roi.json",
        models=root / "models"
    )
    logger = InspectionLogger(band)

    logger.log_if_changed(make_result(True), "clio")

    assert logger.log_if_changed(make_result(False), "clio") is False  # NG #1
    assert logger.log_if_changed(make_result(False), "clio") is False  # NG #2
    assert logger.log_if_changed(make_result(True), "clio") is False   # OK - sayaç sıfırlanır
    assert logger.log_if_changed(make_result(False), "clio") is False  # NG #1 (yeni seri)
    assert logger.log_if_changed(make_result(False), "clio") is False  # NG #2
    assert logger.log_if_changed(make_result(False), "clio") is True   # NG #3 - onaylandı


def test_confirm_frames_is_read_from_band(band):

    band.confirm_frames = 5

    logger = InspectionLogger(band)

    assert logger.confirm_frames == 5


def test_confirm_frames_defaults_to_three_for_band_without_attribute():

    class LegacyBand:
        root = None

    legacy = LegacyBand()

    import tempfile
    from pathlib import Path

    legacy.root = Path(tempfile.mkdtemp())

    logger = InspectionLogger(legacy)

    assert logger.confirm_frames == 3


def test_set_confirm_frames_changes_behavior_live(logger):

    logger.set_confirm_frames(1)

    logger.log_if_changed(make_result(True), "clio")

    # confirm_frames=1 iken tek kare bile geçişi onaylamalı
    assert logger.log_if_changed(make_result(False), "clio") is True


def test_set_confirm_frames_rejects_values_below_one(logger):

    logger.set_confirm_frames(0)

    assert logger.confirm_frames == 1

    logger.set_confirm_frames(-5)

    assert logger.confirm_frames == 1


def test_empty_results_are_never_logged(logger):

    assert logger.log_if_changed({}, "clio") is False


def test_fetch_recent_returns_most_recent_first(logger):

    logger.log_if_changed(make_result(True), "clio")

    for _ in range(InspectionLogger.CONFIRM_FRAMES):
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

    logger.log_if_changed(make_result(True), "clio")  # ilk kayıt, anında

    for _ in range(InspectionLogger.CONFIRM_FRAMES):
        logger.log_if_changed(make_result(False), "clio")  # NG'ye onaylı geçiş

    for _ in range(InspectionLogger.CONFIRM_FRAMES):
        logger.log_if_changed(make_result(True), "clio")  # OK'e onaylı geçiş

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
