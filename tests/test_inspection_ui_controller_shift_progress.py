from datetime import datetime, timedelta

import pytest

from modules.configuration.band import Band
from modules.configuration.inspection_logger import InspectionLogger
from modules.configuration.shift_window import ShiftWindow


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

    band = Band(
        id="band_01",
        name="Test Bandı",
        root=tmp_path / "band_01",
        reference=tmp_path / "band_01" / "reference.png",
        roi=tmp_path / "band_01" / "roi.json",
        models=tmp_path / "band_01" / "models"
    )
    band.root.mkdir(parents=True, exist_ok=True)

    ctrl.current_band = band
    ctrl.inspection_logger = InspectionLogger(band)

    yield ctrl

    window.close()


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


def _window_containing_now(name="Vardiya", margin_minutes=90, operator=""):
    """Şu anı kapsayan bir vardiya penceresi - testin çalıştığı saatten
    bağımsız olması için "now"a göre inşa edilir."""

    now = datetime.now().astimezone()
    start = (now - timedelta(minutes=margin_minutes)).strftime("%H:%M")
    end = (now + timedelta(minutes=margin_minutes)).strftime("%H:%M")

    return ShiftWindow(id=name, name=name, start=start, end=end, operator=operator)


def _window_not_containing_now(name="Eski Vardiya"):
    """Şu andan kesinlikle 2-3 saat önce bitmiş bir pencere."""

    now = datetime.now().astimezone()
    start = (now - timedelta(hours=3)).strftime("%H:%M")
    end = (now - timedelta(hours=2)).strftime("%H:%M")

    return ShiftWindow(id=name, name=name, start=start, end=end)


def test_no_progress_shown_when_no_shifts_defined(controller):

    controller.current_band.shifts = []

    controller._maybe_check_shift_progress()

    assert controller.page.shift_label.text() == "Vardiya: -"


def test_no_progress_shown_when_outside_all_windows(controller):

    controller.current_band.shifts = [_window_not_containing_now()]

    controller._maybe_check_shift_progress()

    assert controller.page.shift_label.text() == "Vardiya: -"


def test_progress_label_reflects_produced_count_and_window_name(controller):

    window = _window_containing_now("Sabah")
    controller.current_band.shifts = [window]

    controller.inspection_logger.log(_make_result(True), "clio")
    controller.inspection_logger.log(_make_result(False), "clio")

    controller._maybe_check_shift_progress()

    text = controller.page.shift_label.text()
    assert "2 kasa" in text
    assert "Sabah" in text
    assert window.start in text
    assert window.end in text


def test_progress_label_includes_assigned_operator(controller):

    window = _window_containing_now("Sabah", operator="Ahmet Yılmaz")
    controller.current_band.shifts = [window]

    controller._maybe_check_shift_progress()

    assert "Ahmet Yılmaz" in controller.page.shift_label.text()


def test_progress_label_omits_operator_when_unassigned(controller):

    window = _window_containing_now("Sabah")
    controller.current_band.shifts = [window]

    controller._maybe_check_shift_progress()

    text = controller.page.shift_label.text()
    assert text.count("—") == 1  # sadece "isim (saat)" ayracı, operatör yok


def test_first_matching_window_wins_when_windows_overlap(controller):

    controller.current_band.shifts = [
        _window_not_containing_now("Önce"),
        _window_containing_now("Aktif"),
    ]

    controller._maybe_check_shift_progress()

    assert "Aktif" in controller.page.shift_label.text()


def test_shift_check_throttles_repeated_calls(controller, monkeypatch):

    controller.current_band.shifts = [_window_containing_now()]

    calls = []

    original = controller.inspection_logger.compute_period_stats

    def counting_compute(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(
        controller.inspection_logger, "compute_period_stats", counting_compute
    )

    controller._maybe_check_shift_progress()
    controller._maybe_check_shift_progress()

    assert len(calls) == 1


def test_shift_progress_resets_on_band_change(controller):

    controller.current_band.shifts = [_window_containing_now()]
    controller._maybe_check_shift_progress()

    assert controller.page.shift_label.text() != "Vardiya: -"

    controller.bands = [controller.current_band]
    controller.models = []

    controller._select_band(0)

    assert controller.page.shift_label.text() == "Vardiya: -"
