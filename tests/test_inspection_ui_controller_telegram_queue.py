from unittest.mock import MagicMock

import pytest

from modules.core.telegram_notification_queue import QueuedNotification
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

    yield ctrl

    # bkz. tests/conftest.py - açık bırakılan pencereler test paketi
    # boyunca Qt native kaynaklarının birikmesine yol açabiliyordu.
    window.close()


# -------------------------------------------------
# _telegram_retry_on_failure_callback
# -------------------------------------------------

def test_failure_callback_enqueues_on_none_message_id(controller):

    callback = controller._telegram_retry_on_failure_callback(
        kind="message",
        bot_token="tok",
        chat_id="123",
        text="merhaba",
        record_id=5,
        is_primary=True
    )

    callback(None)

    queued = controller.telegram_queue.load()

    assert len(queued) == 1
    assert queued[0] == QueuedNotification(
        kind="message",
        bot_token="tok",
        chat_id="123",
        text="merhaba",
        image_path="",
        record_id=5,
        is_primary=True
    )


def test_failure_callback_does_not_enqueue_on_success(controller):

    received = []

    callback = controller._telegram_retry_on_failure_callback(
        kind="message",
        bot_token="tok",
        chat_id="123",
        text="merhaba",
        on_success=lambda message_id: received.append(message_id)
    )

    callback(42)

    assert controller.telegram_queue.load() == []
    assert received == [42]


def test_failure_callback_preserves_photo_fields(controller):

    callback = controller._telegram_retry_on_failure_callback(
        kind="photo",
        bot_token="tok",
        chat_id="123",
        text="caption",
        image_path="/tmp/ng.jpg",
        record_id=9,
        is_primary=False
    )

    callback(None)

    queued = controller.telegram_queue.load()

    assert queued[0].kind == "photo"
    assert queued[0].image_path == "/tmp/ng.jpg"
    assert queued[0].is_primary is False


# -------------------------------------------------
# _maybe_flush_telegram_queue
# -------------------------------------------------

def test_flush_queue_sends_and_updates_message_id(controller, monkeypatch):

    controller.telegram_queue.enqueue(QueuedNotification(
        kind="message",
        bot_token="tok",
        chat_id="123",
        text="merhaba",
        record_id=7,
        is_primary=True
    ))

    fake_logger = MagicMock()
    controller.inspection_logger = fake_logger

    monkeypatch.setattr(
        TelegramNotifier, "send_message", lambda self, text: 999
    )

    controller._maybe_flush_telegram_queue()

    assert controller._telegram_flush_thread is not None
    controller._telegram_flush_thread.join(timeout=5)

    fake_logger.set_telegram_message_id.assert_called_once_with(7, 999)
    assert controller.telegram_queue.load() == []


def test_flush_queue_leaves_item_queued_on_repeated_failure(
    controller, monkeypatch
):

    controller.telegram_queue.enqueue(QueuedNotification(
        kind="message", bot_token="tok", chat_id="123", text="merhaba"
    ))

    monkeypatch.setattr(
        TelegramNotifier, "send_message", lambda self, text: None
    )

    controller._maybe_flush_telegram_queue()
    controller._telegram_flush_thread.join(timeout=5)

    assert len(controller.telegram_queue.load()) == 1


def test_maybe_flush_throttles_repeated_calls(controller, monkeypatch):

    calls = []
    original_flush = controller.telegram_queue.flush

    def counting_flush(*args, **kwargs):

        calls.append(1)

        return original_flush(*args, **kwargs)

    monkeypatch.setattr(controller.telegram_queue, "flush", counting_flush)

    controller._maybe_flush_telegram_queue()

    if controller._telegram_flush_thread is not None:
        controller._telegram_flush_thread.join(timeout=5)

    # Hemen art arda çağrıldığında ikinci çağrı, throttle penceresi
    # (TELEGRAM_QUEUE_FLUSH_INTERVAL_SECONDS) dolmadığı için yeni bir
    # flush BAŞLATMAMALI.
    controller._maybe_flush_telegram_queue()

    if controller._telegram_flush_thread is not None:
        controller._telegram_flush_thread.join(timeout=5)

    assert len(calls) == 1
