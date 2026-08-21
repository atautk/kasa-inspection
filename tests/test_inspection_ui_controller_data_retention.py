from datetime import datetime, timezone, timedelta

import pytest

from modules.configuration.band_manager import BandManager


@pytest.fixture(scope="module")
def qapp():

    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


@pytest.fixture
def controller(qapp, tmp_path):

    from modules.ui.inspection.inspection_window import InspectionWindow
    from modules.ui.inspection.inspection_ui_controller import (
        InspectionUIController
    )
    from modules.configuration.inspection_logger import InspectionLogger

    window = InspectionWindow()

    ctrl = InspectionUIController(window, root=tmp_path, operator_name="test")

    ctrl.band_manager = BandManager(root=tmp_path / "configuration")

    band = ctrl.band_manager.create_band("Test Bandı")

    ctrl.current_band = band
    ctrl.inspection_logger = InspectionLogger(band)

    yield ctrl

    window.close()


def _wait_for_retention_thread(controller):

    if controller._data_retention_thread is not None:
        controller._data_retention_thread.join(timeout=5)


def _make_result(ok):

    return {
        "G01": {
            "state": "FULL",
            "expected": "FULL" if ok else "EMPTY",
            "ok": ok,
            "change_ratio": 1.0,
            "changed_pixels": 1
        }
    }


def test_disabled_when_not_enabled(controller):

    controller.current_band.data_retention_enabled = False

    controller._maybe_run_data_retention()

    assert controller._data_retention_thread is None


def test_disabled_when_no_destination(controller):

    controller.current_band.data_retention_enabled = True
    controller.current_band.data_retention_export_destination = ""

    controller._maybe_run_data_retention()

    assert controller._data_retention_thread is None


def test_runs_and_persists_last_run_time(controller, tmp_path):

    destination = tmp_path / "archive"

    controller.inspection_logger.log(_make_result(True), "clio")
    old_id = controller.inspection_logger.last_inserted_id

    conn = controller.inspection_logger._connect()
    conn.execute(
        "UPDATE inspections SET timestamp = ? WHERE id = ?",
        ("2000-01-01T00:00:00+00:00", old_id)
    )
    conn.commit()
    conn.close()

    controller.current_band.data_retention_enabled = True
    controller.current_band.data_retention_export_destination = str(
        destination
    )
    controller.current_band.data_retention_period_value = 1
    controller.current_band.data_retention_period_unit = "year"
    controller.current_band.last_data_retention_run_at = ""

    controller._maybe_run_data_retention()
    _wait_for_retention_thread(controller)

    assert list(destination.iterdir())
    assert controller.current_band.last_data_retention_run_at != ""

    reloaded = controller.band_manager.load_band(controller.current_band.id)
    assert reloaded.last_data_retention_run_at != ""


def test_skips_when_check_interval_not_yet_elapsed(controller, tmp_path):

    destination = tmp_path / "archive"

    recent = datetime.now(timezone.utc) - timedelta(hours=1)

    controller.current_band.data_retention_enabled = True
    controller.current_band.data_retention_export_destination = str(
        destination
    )
    controller.current_band.last_data_retention_run_at = recent.isoformat()

    controller._maybe_run_data_retention()

    assert controller._data_retention_thread is None
    assert not destination.exists()


def test_check_throttles_repeated_calls(controller, tmp_path, monkeypatch):

    destination = tmp_path / "archive"

    controller.current_band.data_retention_enabled = True
    controller.current_band.data_retention_export_destination = str(
        destination
    )

    calls = []
    original = controller.data_retention_manager.export_and_purge

    def counting(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(
        controller.data_retention_manager, "export_and_purge", counting
    )

    controller._maybe_run_data_retention()
    _wait_for_retention_thread(controller)

    controller._maybe_run_data_retention()
    _wait_for_retention_thread(controller)

    assert len(calls) == 1


def test_retention_failure_does_not_crash_or_update_timestamp(
    controller, tmp_path, monkeypatch
):

    destination = tmp_path / "archive"

    controller.current_band.data_retention_enabled = True
    controller.current_band.data_retention_export_destination = str(
        destination
    )
    controller.current_band.last_data_retention_run_at = ""

    def failing(*args, **kwargs):
        raise OSError("disk erişilemiyor")

    monkeypatch.setattr(
        controller.data_retention_manager, "export_and_purge", failing
    )

    controller._maybe_run_data_retention()
    _wait_for_retention_thread(controller)

    assert controller.current_band.last_data_retention_run_at == ""
