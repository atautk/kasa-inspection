from datetime import datetime, timezone, timedelta

import pytest

from modules.configuration.band import Band
from modules.configuration.inspection_logger import InspectionLogger
from modules.configuration.telegram_settings import TelegramSettings
from modules.core.telegram_notifier import TelegramNotifier


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
        models=tmp_path / "band_01" / "models",
        shift_target_count=200,
        shift_duration_hours=8.0
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


def test_no_progress_shown_when_shift_not_started(controller):

    controller.shift_start_time = None

    controller._maybe_check_shift_progress()

    assert controller.page.shift_label.text() == "Vardiya: -"


def test_no_progress_shown_when_target_is_zero(controller):

    controller.current_band.shift_target_count = 0
    controller.shift_start_time = datetime.now(timezone.utc)

    controller._maybe_check_shift_progress()

    assert controller.page.shift_label.text() == "Vardiya: -"


def test_progress_label_reflects_produced_count(controller):

    controller.shift_start_time = datetime.now(timezone.utc) - timedelta(
        hours=1
    )

    controller.inspection_logger.log(_make_result(True), "clio")
    controller.inspection_logger.log(_make_result(False), "clio")

    controller._maybe_check_shift_progress()

    assert "2 / 200" in controller.page.shift_label.text()


def test_shift_check_throttles_repeated_calls(controller, monkeypatch):

    controller.shift_start_time = datetime.now(timezone.utc)

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


def test_no_warning_when_on_pace(controller, monkeypatch):

    controller.telegram_settings_manager.save(
        TelegramSettings(bot_token="tok", chat_id="chat")
    )

    # 1 saat geçti (8 saatlik vardiyanın 1/8'i = %12.5), hedefin
    # %12.5'i = 25 kasa gerekir; 30 kasa üretilmiş -> tempoda.
    controller.shift_start_time = datetime.now(timezone.utc) - timedelta(
        hours=1
    )

    for _ in range(30):
        controller.inspection_logger.log(_make_result(True), "clio")

    sent = []

    monkeypatch.setattr(
        TelegramNotifier,
        "send_message",
        lambda self, text: (sent.append(text), 1)[1]
    )

    controller._maybe_check_shift_progress()

    assert sent == []


def test_warning_sent_when_behind_pace(controller, monkeypatch):

    controller.telegram_settings_manager.save(
        TelegramSettings(bot_token="tok", chat_id="chat")
    )

    # 4 saat geçti (8 saatlik vardiyanın yarısı), hedefin yarısı
    # (100) beklenir; sadece 5 kasa üretilmiş -> ciddi şekilde geride.
    controller.shift_start_time = datetime.now(timezone.utc) - timedelta(
        hours=4
    )

    for _ in range(5):
        controller.inspection_logger.log(_make_result(True), "clio")

    sent = []

    monkeypatch.setattr(
        TelegramNotifier,
        "send_message",
        lambda self, text: (sent.append(text), 1)[1]
    )

    controller._maybe_check_shift_progress()

    assert len(sent) == 1
    assert "Test Bandı" in sent[0]
    assert "5 / 200" in sent[0]


def test_warning_cooldown_prevents_immediate_repeat(controller, monkeypatch):

    controller.telegram_settings_manager.save(
        TelegramSettings(bot_token="tok", chat_id="chat")
    )

    controller.shift_start_time = datetime.now(timezone.utc) - timedelta(
        hours=4
    )

    sent = []

    monkeypatch.setattr(
        TelegramNotifier,
        "send_message",
        lambda self, text: (sent.append(text), 1)[1]
    )

    controller._last_shift_check_attempt = 0.0
    controller._maybe_check_shift_progress()

    controller._last_shift_check_attempt = 0.0
    controller._maybe_check_shift_progress()

    assert len(sent) == 1


def test_shift_state_resets_on_band_change(controller):

    controller.shift_start_time = datetime.now(timezone.utc)
    controller._last_shift_warning_at = 123.0

    controller.bands = [controller.current_band]
    controller.models = []

    controller._select_band(0)

    assert controller.shift_start_time is None
    assert controller._last_shift_warning_at is None
    assert controller.page.shift_label.text() == "Vardiya: -"
