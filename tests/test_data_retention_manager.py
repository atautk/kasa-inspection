import pytest

from modules.configuration.band import Band
from modules.configuration.inspection_logger import InspectionLogger
from modules.configuration.data_retention_manager import DataRetentionManager


@pytest.fixture
def band(tmp_path):

    return Band(
        id="test_band",
        name="Test Band",
        root=tmp_path,
        reference=tmp_path / "reference.png",
        roi=tmp_path / "roi.json",
        models=tmp_path / "models",
        data_retention_period_value=1,
        data_retention_period_unit="year"
    )


@pytest.fixture
def logger(band):

    return InspectionLogger(band)


@pytest.fixture
def manager():

    return DataRetentionManager()


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


def _set_timestamp(logger, record_id, iso_timestamp):

    conn = logger._connect()
    conn.execute(
        "UPDATE inspections SET timestamp = ? WHERE id = ?",
        (iso_timestamp, record_id)
    )
    conn.commit()
    conn.close()


@pytest.mark.parametrize(
    "period_value, period_unit, expected_days",
    [
        (1, "day", 1),
        (5, "day", 5),
        (1, "month", 30),
        (6, "month", 180),
        (1, "year", 365),
        (2, "year", 730),
        (1, "unknown_unit", 365),
        (0, "day", 1),
    ]
)
def test_resolve_max_days(manager, period_value, period_unit, expected_days):

    assert manager.resolve_max_days(period_value, period_unit) == expected_days


def test_export_and_purge_with_no_old_records_does_nothing(
    manager, band, logger, tmp_path
):

    logger.log(make_result(True), "clio")

    destination = tmp_path / "archive"

    result = manager.export_and_purge(band, logger, destination)

    assert result is None
    assert not destination.exists()
    assert len(logger.fetch_recent(100)) == 1


def test_export_and_purge_archives_and_deletes_old_records(
    manager, band, logger, tmp_path
):

    logger.log(make_result(True), "clio")
    old_id = logger.last_inserted_id

    logger.log(make_result(False), "clio")
    new_id = logger.last_inserted_id

    _set_timestamp(logger, old_id, "2000-01-01T00:00:00+00:00")

    destination = tmp_path / "archive"

    band.data_retention_period_value = 1
    band.data_retention_period_unit = "year"

    report_path = manager.export_and_purge(band, logger, destination)

    assert report_path is not None
    assert report_path.exists()
    assert report_path.parent == destination

    remaining_ids = [row["id"] for row in logger.fetch_recent(100)]
    assert remaining_ids == [new_id]


def test_export_and_purge_removes_old_image_files(
    manager, band, logger, tmp_path
):

    old_image = tmp_path / "ng_captures" / "old.png"
    old_image.parent.mkdir(parents=True, exist_ok=True)
    old_image.write_bytes(b"fake image")

    logger.log(make_result(False), "clio", image_path=str(old_image))
    old_id = logger.last_inserted_id

    _set_timestamp(logger, old_id, "2000-01-01T00:00:00+00:00")

    destination = tmp_path / "archive"

    manager.export_and_purge(band, logger, destination)

    assert not old_image.exists()


def test_export_and_purge_creates_destination_folder(
    manager, band, logger, tmp_path
):

    logger.log(make_result(True), "clio")
    old_id = logger.last_inserted_id

    _set_timestamp(logger, old_id, "2000-01-01T00:00:00+00:00")

    destination = tmp_path / "does" / "not" / "exist_yet"

    manager.export_and_purge(band, logger, destination)

    assert destination.exists()
