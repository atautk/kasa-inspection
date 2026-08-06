import json
from datetime import datetime, timedelta

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


def test_compute_period_stats_excludes_records_before_since(logger):

    logger.log(make_result(True), "clio")
    logger.log(make_result(False), "clio")

    # ilk kaydı "eskiymiş" gibi göstermek için zaman damgasını geriye al
    conn = logger._connect()
    conn.execute(
        "UPDATE inspections SET timestamp = ? WHERE id = ?",
        ("2000-01-01T00:00:00+00:00", logger.fetch_recent()[-1]["id"])
    )
    conn.commit()
    conn.close()

    stats = logger.compute_period_stats("2020-01-01T00:00:00+00:00")

    assert stats["total"] == 1
    assert stats["ok_count"] == 0
    assert stats["ng_count"] == 1


def test_compute_period_stats_with_future_since_returns_empty(logger):

    logger.log(make_result(True), "clio")

    stats = logger.compute_period_stats("2999-01-01T00:00:00+00:00")

    assert stats["total"] == 0
    assert stats["by_model"] == {}
    assert stats["by_roi"] == {}


def test_compute_period_stats_matches_compute_stats_shape(logger):

    logger.log(make_result(True), "clio")

    stats = logger.compute_period_stats("2000-01-01T00:00:00+00:00")

    assert set(stats.keys()) == {
        "total", "ok_count", "ng_count", "by_model", "by_roi"
    }


def _local_iso(hour, minute=0, day_offset=0):
    """
    Yerel saatte (makine hangi zaman diliminde olursa olsun) belirli
    bir saat/dakikaya denk gelen bir ISO zaman damgası üretir - bu
    sayede compute_shift_trend'in kullandığı .astimezone() dönüşümü
    testte de aynı yerel saati verir, test makinesinin zaman dilimine
    bağımlı olmadan.
    """

    now = datetime.now().astimezone()

    dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if day_offset:
        dt = dt + timedelta(days=day_offset)

    return dt.isoformat()


def _set_timestamp(logger, record_id, iso_timestamp):

    conn = logger._connect()
    conn.execute(
        "UPDATE inspections SET timestamp = ? WHERE id = ?",
        (iso_timestamp, record_id)
    )
    conn.commit()
    conn.close()


def test_shift_trend_buckets_by_shift_duration(logger):

    logger.log(make_result(True), "clio")
    id_morning = logger.last_inserted_id

    logger.log(make_result(False), "clio")
    id_afternoon = logger.last_inserted_id

    # 8 saatlik vardiyalarda: 02:00 -> 00:00-08:00 vardiyası,
    # 10:00 -> 08:00-16:00 vardiyası (farklı vardiyalar).
    _set_timestamp(logger, id_morning, _local_iso(hour=2))
    _set_timestamp(logger, id_afternoon, _local_iso(hour=10))

    trend = logger.compute_shift_trend(shift_duration_hours=8.0)

    assert len(trend) == 2
    assert trend[0]["ok"] == 1 and trend[0]["ng"] == 0
    assert trend[1]["ok"] == 0 and trend[1]["ng"] == 1


def test_shift_trend_same_shift_aggregates_together(logger):

    logger.log(make_result(True), "clio")
    id_a = logger.last_inserted_id

    logger.log(make_result(False), "clio")
    id_b = logger.last_inserted_id

    # İkisi de aynı 00:00-08:00 vardiyasında.
    _set_timestamp(logger, id_a, _local_iso(hour=1))
    _set_timestamp(logger, id_b, _local_iso(hour=6))

    trend = logger.compute_shift_trend(shift_duration_hours=8.0)

    assert len(trend) == 1
    assert trend[0]["total"] == 2
    assert trend[0]["ok"] == 1
    assert trend[0]["ng"] == 1
    assert trend[0]["ng_ratio"] == 50.0


def test_shift_trend_date_label_matches_shift_start(logger):

    logger.log(make_result(True), "clio")

    _set_timestamp(logger, logger.last_inserted_id, _local_iso(hour=10))

    trend = logger.compute_shift_trend(shift_duration_hours=8.0)

    # 10:00 -> 08:00-16:00 vardiyası, etiket vardiyanın BAŞLANGICI olmalı
    assert trend[0]["date"].endswith("08:00")


def test_shift_trend_respects_limit_shifts(logger):

    for hour in (0, 8, 16):

        logger.log(make_result(True), "clio")
        _set_timestamp(
            logger, logger.last_inserted_id, _local_iso(hour=hour)
        )

    trend = logger.compute_shift_trend(
        shift_duration_hours=8.0, limit_shifts=2
    )

    assert len(trend) == 2


def test_shift_trend_non_positive_duration_falls_back_to_default(logger):

    logger.log(make_result(True), "clio")
    _set_timestamp(logger, logger.last_inserted_id, _local_iso(hour=2))

    trend_zero = logger.compute_shift_trend(shift_duration_hours=0)
    trend_negative = logger.compute_shift_trend(shift_duration_hours=-5)
    trend_default = logger.compute_shift_trend(shift_duration_hours=8.0)

    assert trend_zero == trend_default
    assert trend_negative == trend_default


def test_shift_trend_empty_when_no_records(logger):

    assert logger.compute_shift_trend(shift_duration_hours=8.0) == []


def test_clear_removes_all_records_and_resets_state(logger):

    logger.log_if_changed(make_result(True), "clio")

    logger.clear()

    assert logger.fetch_recent() == []
    assert logger.last_overall_result is None


def test_log_exposes_inserted_record_id(logger):

    logger.log(make_result(False), "clio")

    assert logger.last_inserted_id is not None
    assert logger.last_inserted_id == logger.fetch_recent()[0]["id"]


def test_set_and_find_telegram_message_id(logger):

    logger.log(make_result(False), "clio")
    record_id = logger.last_inserted_id

    logger.set_telegram_message_id(record_id, 987654)

    found = logger.find_record_by_telegram_message_id(987654)

    assert found == record_id


def test_find_telegram_message_id_unknown_returns_none(logger):

    assert logger.find_record_by_telegram_message_id(111) is None


def test_telegram_reaction_can_mark_ng_as_reviewed_ok(logger):
    """
    Uçtan uca: NG loglanır, Telegram mesaj id'si eşleştirilir,
    reaksiyon geldiğinde mark_reviewed_ok ile OK'e çevrilebilir.
    """

    logger.log(make_result(False), "clio")
    record_id = logger.last_inserted_id

    logger.set_telegram_message_id(record_id, 555)

    found_id = logger.find_record_by_telegram_message_id(555)
    logger.mark_reviewed_ok(found_id, operator_name="Telegram")

    row = logger.fetch_recent()[0]

    assert row["overall_result"] == "OK"
    assert row["original_result"] == "NG"
    assert row["reviewed"] == 1
    assert row["reviewed_by"] == "Telegram"
