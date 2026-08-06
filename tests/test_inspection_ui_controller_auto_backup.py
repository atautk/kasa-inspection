from datetime import datetime, timezone, timedelta

import pytest

from modules.configuration.band import Band
from modules.configuration.band_manager import BandManager
from modules.configuration.backup_manager import BackupManager


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

    window = InspectionWindow()

    ctrl = InspectionUIController(window, root=tmp_path, operator_name="test")

    ctrl.band_manager = BandManager(root=tmp_path / "configuration")

    band = ctrl.band_manager.create_band("Test Bandı")
    (band.root / "inspection_log.db").write_bytes(b"data")

    ctrl.current_band = band

    yield ctrl

    window.close()


def _wait_for_backup_thread(controller):

    if controller._backup_thread is not None:
        controller._backup_thread.join(timeout=5)


def test_disabled_when_not_enabled(controller):

    controller.current_band.auto_backup_enabled = False

    controller._maybe_run_auto_backup()

    assert controller._backup_thread is None


def test_disabled_when_no_destination(controller):

    controller.current_band.auto_backup_enabled = True
    controller.current_band.auto_backup_destination = ""

    controller._maybe_run_auto_backup()

    assert controller._backup_thread is None


def test_runs_backup_when_never_run_before(controller, tmp_path):

    destination = tmp_path / "backups"
    destination.mkdir()

    controller.current_band.auto_backup_enabled = True
    controller.current_band.auto_backup_destination = str(destination)
    controller.current_band.last_auto_backup_at = ""

    controller._maybe_run_auto_backup()
    _wait_for_backup_thread(controller)

    backups = list(destination.iterdir())
    assert len(backups) == 1
    assert controller.current_band.last_auto_backup_at != ""


def test_persists_last_backup_time_to_disk(controller, tmp_path):

    destination = tmp_path / "backups"
    destination.mkdir()

    controller.current_band.auto_backup_enabled = True
    controller.current_band.auto_backup_destination = str(destination)

    controller._maybe_run_auto_backup()
    _wait_for_backup_thread(controller)

    reloaded = controller.band_manager.load_band(controller.current_band.id)
    assert reloaded.last_auto_backup_at != ""


def test_skips_when_interval_not_yet_elapsed(controller, tmp_path):

    destination = tmp_path / "backups"
    destination.mkdir()

    recent = datetime.now(timezone.utc) - timedelta(hours=1)

    controller.current_band.auto_backup_enabled = True
    controller.current_band.auto_backup_destination = str(destination)
    controller.current_band.auto_backup_interval_hours = 24.0
    controller.current_band.last_auto_backup_at = recent.isoformat()

    controller._maybe_run_auto_backup()

    assert controller._backup_thread is None
    assert list(destination.iterdir()) == []


def test_runs_when_interval_elapsed(controller, tmp_path):

    destination = tmp_path / "backups"
    destination.mkdir()

    old = datetime.now(timezone.utc) - timedelta(hours=48)

    controller.current_band.auto_backup_enabled = True
    controller.current_band.auto_backup_destination = str(destination)
    controller.current_band.auto_backup_interval_hours = 24.0
    controller.current_band.last_auto_backup_at = old.isoformat()

    controller._maybe_run_auto_backup()
    _wait_for_backup_thread(controller)

    assert len(list(destination.iterdir())) == 1


def test_check_throttles_repeated_calls(controller, tmp_path, monkeypatch):

    destination = tmp_path / "backups"
    destination.mkdir()

    controller.current_band.auto_backup_enabled = True
    controller.current_band.auto_backup_destination = str(destination)

    calls = []
    original = controller.backup_manager.backup_and_cleanup

    def counting(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(
        controller.backup_manager, "backup_and_cleanup", counting
    )

    controller._maybe_run_auto_backup()
    _wait_for_backup_thread(controller)

    controller._maybe_run_auto_backup()
    _wait_for_backup_thread(controller)

    assert len(calls) == 1


def test_enforces_keep_count(controller, tmp_path):

    destination = tmp_path / "backups"
    destination.mkdir()

    for suffix in ["20260101_000000", "20260102_000000", "20260103_000000"]:
        (
            destination / f"{controller.current_band.name}_yedek_{suffix}"
        ).mkdir()

    controller.current_band.auto_backup_enabled = True
    controller.current_band.auto_backup_destination = str(destination)
    controller.current_band.auto_backup_keep_count = 2

    controller._maybe_run_auto_backup()
    _wait_for_backup_thread(controller)

    assert len(list(destination.iterdir())) == 2


def test_backup_failure_does_not_crash_or_update_timestamp(
    controller, tmp_path, monkeypatch
):

    destination = tmp_path / "backups"
    destination.mkdir()

    controller.current_band.auto_backup_enabled = True
    controller.current_band.auto_backup_destination = str(destination)
    controller.current_band.last_auto_backup_at = ""

    def failing(*args, **kwargs):
        raise OSError("disk erişilemiyor")

    monkeypatch.setattr(
        controller.backup_manager, "backup_and_cleanup", failing
    )

    controller._maybe_run_auto_backup()
    _wait_for_backup_thread(controller)

    assert controller.current_band.last_auto_backup_at == ""
