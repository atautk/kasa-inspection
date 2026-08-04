import threading
import time
from unittest.mock import patch, MagicMock

import pytest

from modules.core.telegram_notifier import TelegramNotifier


def _fake_response(ok=True, status_code=200, text=""):

    response = MagicMock()
    response.ok = ok
    response.status_code = status_code
    response.text = text

    return response


def test_is_configured_requires_both_fields():

    assert TelegramNotifier("", "").is_configured() is False
    assert TelegramNotifier("token", "").is_configured() is False
    assert TelegramNotifier("", "chat").is_configured() is False
    assert TelegramNotifier("token", "chat").is_configured() is True


def test_send_message_skips_network_call_when_not_configured():

    notifier = TelegramNotifier("", "")

    with patch(
        "modules.core.telegram_notifier.requests.post"
    ) as mock_post:

        result = notifier.send_message("merhaba")

        assert result is False
        assert not mock_post.called


def test_send_message_success():

    notifier = TelegramNotifier("token", "chat")

    with patch(
        "modules.core.telegram_notifier.requests.post",
        return_value=_fake_response(ok=True)
    ) as mock_post:

        result = notifier.send_message("merhaba")

        assert result is True

        args, kwargs = mock_post.call_args
        assert "sendMessage" in args[0]
        assert kwargs["data"]["chat_id"] == "chat"
        assert kwargs["data"]["text"] == "merhaba"


def test_send_message_failure_response_returns_false():

    notifier = TelegramNotifier("token", "chat")

    with patch(
        "modules.core.telegram_notifier.requests.post",
        return_value=_fake_response(ok=False, status_code=401, text="bad token")
    ):

        assert notifier.send_message("merhaba") is False


def test_send_message_network_exception_does_not_raise():

    notifier = TelegramNotifier("token", "chat")

    with patch(
        "modules.core.telegram_notifier.requests.post",
        side_effect=ConnectionError("no internet")
    ):

        assert notifier.send_message("merhaba") is False


def test_send_photo_success(tmp_path):

    image_path = tmp_path / "ng.png"
    image_path.write_bytes(b"fake png bytes")

    notifier = TelegramNotifier("token", "chat")

    with patch(
        "modules.core.telegram_notifier.requests.post",
        return_value=_fake_response(ok=True)
    ) as mock_post:

        result = notifier.send_photo(str(image_path), caption="NG!")

        assert result is True

        args, kwargs = mock_post.call_args
        assert "sendPhoto" in args[0]
        assert kwargs["data"]["caption"] == "NG!"
        assert "photo" in kwargs["files"]


def test_send_photo_missing_file_does_not_raise():

    notifier = TelegramNotifier("token", "chat")

    with patch("modules.core.telegram_notifier.requests.post") as mock_post:

        result = notifier.send_photo("/does/not/exist.png")

        assert result is False
        assert not mock_post.called


def test_send_message_async_runs_in_background_thread():

    notifier = TelegramNotifier("token", "chat")

    call_thread_names = []

    def fake_post(*args, **kwargs):
        call_thread_names.append(threading.current_thread().name)
        return _fake_response(ok=True)

    with patch(
        "modules.core.telegram_notifier.requests.post",
        side_effect=fake_post
    ):

        main_thread_name = threading.current_thread().name

        notifier.send_message_async("merhaba")

        # arka plan thread'inin bitmesini bekle
        deadline = time.time() + 2
        while not call_thread_names and time.time() < deadline:
            time.sleep(0.01)

    assert call_thread_names, "arka plan thread hic cagrilmadi"
    assert call_thread_names[0] != main_thread_name
