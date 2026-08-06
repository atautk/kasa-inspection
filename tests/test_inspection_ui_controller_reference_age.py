import os
import time

import cv2
import numpy as np
import pytest

from modules.configuration.band import Band
from modules.configuration.camera_channel import CameraChannel
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
        reference_max_age_days=0
    )
    band.root.mkdir(parents=True, exist_ok=True)

    ctrl.current_band = band

    yield ctrl

    window.close()


def _write_reference(path, age_days=0):

    path.parent.mkdir(parents=True, exist_ok=True)

    cv2.imwrite(str(path), np.zeros((10, 10, 3), dtype=np.uint8))

    if age_days:

        old_time = time.time() - age_days * 86400

        os.utime(path, (old_time, old_time))


def test_disabled_when_max_age_is_zero(controller):

    controller.current_band.reference_max_age_days = 0
    _write_reference(controller.current_band.reference, age_days=100)

    controller._maybe_check_reference_age()

    assert controller.page.reference_age_warning_banner.isHidden()


def test_no_warning_for_fresh_reference(controller):

    controller.current_band.reference_max_age_days = 30
    _write_reference(controller.current_band.reference, age_days=1)

    controller._maybe_check_reference_age()

    assert controller.page.reference_age_warning_banner.isHidden()


def test_warning_shown_for_stale_reference(controller):

    controller.current_band.reference_max_age_days = 30
    _write_reference(controller.current_band.reference, age_days=45)

    controller._maybe_check_reference_age()

    assert not controller.page.reference_age_warning_banner.isHidden()


def test_missing_reference_file_does_not_warn(controller):

    controller.current_band.reference_max_age_days = 30
    # reference.png hiç oluşturulmadı

    controller._maybe_check_reference_age()

    assert controller.page.reference_age_warning_banner.isHidden()


def test_stale_extra_channel_reference_is_named_in_warning(controller):

    controller.current_band.reference_max_age_days = 30
    _write_reference(controller.current_band.reference, age_days=1)

    channel = CameraChannel(
        id="ch1",
        name="Yan",
        camera_index=1,
        reference=controller.current_band.root / "cameras" / "ch1" / "reference.png",
        roi=controller.current_band.root / "cameras" / "ch1" / "roi.json"
    )
    controller.current_band.cameras = [channel]

    _write_reference(channel.reference, age_days=45)

    controller._maybe_check_reference_age()

    assert not controller.page.reference_age_warning_banner.isHidden()
    assert "Yan" in controller.page.reference_age_warning_banner.text()
    assert "Birincil" not in controller.page.reference_age_warning_banner.text()


def test_check_throttles_repeated_calls(controller, monkeypatch):

    controller.current_band.reference_max_age_days = 30
    _write_reference(controller.current_band.reference, age_days=45)

    calls = []

    original = controller._find_stale_reference_channels

    def counting(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(
        controller, "_find_stale_reference_channels", counting
    )

    controller._maybe_check_reference_age()
    controller._maybe_check_reference_age()

    assert len(calls) == 1


def test_stale_reference_sends_telegram_warning(controller, monkeypatch):

    controller.telegram_settings_manager.save(
        TelegramSettings(bot_token="tok", chat_id="chat")
    )

    controller.current_band.reference_max_age_days = 30
    _write_reference(controller.current_band.reference, age_days=45)

    sent = []

    monkeypatch.setattr(
        TelegramNotifier,
        "send_message",
        lambda self, text: (sent.append(text), 1)[1]
    )

    controller._maybe_check_reference_age()

    assert len(sent) == 1
    assert "Test Bandı" in sent[0]
    assert "Birincil" in sent[0]


def test_warning_cooldown_prevents_immediate_repeat(controller, monkeypatch):

    controller.telegram_settings_manager.save(
        TelegramSettings(bot_token="tok", chat_id="chat")
    )

    controller.current_band.reference_max_age_days = 30
    _write_reference(controller.current_band.reference, age_days=45)

    sent = []

    monkeypatch.setattr(
        TelegramNotifier,
        "send_message",
        lambda self, text: (sent.append(text), 1)[1]
    )

    controller._last_reference_age_check_attempt = 0.0
    controller._maybe_check_reference_age()

    controller._last_reference_age_check_attempt = 0.0
    controller._maybe_check_reference_age()

    assert len(sent) == 1


def test_state_resets_on_band_change(controller):

    controller.current_band.reference_max_age_days = 30
    _write_reference(controller.current_band.reference, age_days=45)

    controller._maybe_check_reference_age()
    assert not controller.page.reference_age_warning_banner.isHidden()

    controller.bands = [controller.current_band]
    controller.models = []

    controller._select_band(0)

    assert controller.page.reference_age_warning_banner.isHidden()
    assert controller._last_reference_age_warning_at is None
