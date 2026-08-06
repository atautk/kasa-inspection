import numpy as np
import pytest

from modules.configuration.band import Band
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
        blur_threshold=100.0
    )
    band.root.mkdir(parents=True, exist_ok=True)

    ctrl.current_band = band

    yield ctrl

    window.close()


def _sharp_frame():

    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    frame[::10, :] = 255
    frame[:, ::10] = 255

    return frame


def _blurry_frame():

    return np.full((200, 200, 3), 128, dtype=np.uint8)


def test_sharp_frame_does_not_show_warning(controller):

    controller._maybe_check_blur(_sharp_frame())

    assert controller.page.blur_warning_banner.isHidden()
    assert controller.blur_streak == 0


def test_single_blurry_frame_does_not_warn_yet(controller):

    controller._last_blur_check_attempt = 0.0
    controller._maybe_check_blur(_blurry_frame())

    assert controller.blur_streak == 1
    assert controller.page.blur_warning_banner.isHidden()


def test_sustained_blur_shows_warning(controller):

    for _ in range(controller.BLUR_STREAK_THRESHOLD):
        controller._last_blur_check_attempt = 0.0
        controller._maybe_check_blur(_blurry_frame())

    assert not controller.page.blur_warning_banner.isHidden()


def test_sharp_frame_resets_streak_and_hides_warning(controller):

    for _ in range(controller.BLUR_STREAK_THRESHOLD):
        controller._last_blur_check_attempt = 0.0
        controller._maybe_check_blur(_blurry_frame())

    controller._last_blur_check_attempt = 0.0
    controller._maybe_check_blur(_sharp_frame())

    assert controller.blur_streak == 0
    assert controller.page.blur_warning_banner.isHidden()


def test_blur_check_throttles_repeated_calls(controller):

    controller._maybe_check_blur(_blurry_frame())
    streak_after_first = controller.blur_streak

    controller._maybe_check_blur(_blurry_frame())

    assert controller.blur_streak == streak_after_first


def test_sustained_blur_sends_telegram_warning(controller, monkeypatch):

    controller.telegram_settings_manager.save(
        TelegramSettings(bot_token="tok", chat_id="chat")
    )

    sent = []

    monkeypatch.setattr(
        TelegramNotifier,
        "send_message",
        lambda self, text: (sent.append(text), 1)[1]
    )

    for _ in range(controller.BLUR_STREAK_THRESHOLD):
        controller._last_blur_check_attempt = 0.0
        controller._maybe_check_blur(_blurry_frame())

    assert len(sent) == 1
    assert "Test Bandı" in sent[0]


def test_blur_warning_cooldown_prevents_immediate_repeat(
    controller, monkeypatch
):

    controller.telegram_settings_manager.save(
        TelegramSettings(bot_token="tok", chat_id="chat")
    )

    sent = []

    monkeypatch.setattr(
        TelegramNotifier,
        "send_message",
        lambda self, text: (sent.append(text), 1)[1]
    )

    for _ in range(controller.BLUR_STREAK_THRESHOLD + 3):
        controller._last_blur_check_attempt = 0.0
        controller._maybe_check_blur(_blurry_frame())

    assert len(sent) == 1
