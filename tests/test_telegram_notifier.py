import threading
import time
from unittest.mock import patch, MagicMock

import pytest

from modules.core.telegram_notifier import TelegramNotifier


def _fake_response(ok=True, status_code=200, text="", message_id=42):

    response = MagicMock()
    response.ok = ok
    response.status_code = status_code
    response.text = text
    response.json.return_value = {"result": {"message_id": message_id}}

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

        assert result is None
        assert not mock_post.called


def test_send_message_success_returns_message_id():

    notifier = TelegramNotifier("token", "chat")

    with patch(
        "modules.core.telegram_notifier.requests.post",
        return_value=_fake_response(ok=True, message_id=123)
    ) as mock_post:

        result = notifier.send_message("merhaba")

        assert result == 123

        args, kwargs = mock_post.call_args
        assert "sendMessage" in args[0]
        assert kwargs["data"]["chat_id"] == "chat"
        assert kwargs["data"]["text"] == "merhaba"


def test_send_message_failure_response_returns_none():

    notifier = TelegramNotifier("token", "chat")

    with patch(
        "modules.core.telegram_notifier.requests.post",
        return_value=_fake_response(ok=False, status_code=401, text="bad token")
    ):

        assert notifier.send_message("merhaba") is None


def test_send_message_network_exception_does_not_raise():

    notifier = TelegramNotifier("token", "chat")

    with patch(
        "modules.core.telegram_notifier.requests.post",
        side_effect=ConnectionError("no internet")
    ):

        assert notifier.send_message("merhaba") is None


def test_send_message_unparseable_response_returns_none():

    notifier = TelegramNotifier("token", "chat")

    bad_response = MagicMock()
    bad_response.ok = True
    bad_response.json.side_effect = ValueError("not json")

    with patch(
        "modules.core.telegram_notifier.requests.post",
        return_value=bad_response
    ):

        assert notifier.send_message("merhaba") is None


def test_send_photo_success_returns_message_id(tmp_path):

    image_path = tmp_path / "ng.png"
    image_path.write_bytes(b"fake png bytes")

    notifier = TelegramNotifier("token", "chat")

    with patch(
        "modules.core.telegram_notifier.requests.post",
        return_value=_fake_response(ok=True, message_id=99)
    ) as mock_post:

        result = notifier.send_photo(str(image_path), caption="NG!")

        assert result == 99

        args, kwargs = mock_post.call_args
        assert "sendPhoto" in args[0]
        assert kwargs["data"]["caption"] == "NG!"
        assert "photo" in kwargs["files"]


def test_send_photo_missing_file_does_not_raise():

    notifier = TelegramNotifier("token", "chat")

    with patch("modules.core.telegram_notifier.requests.post") as mock_post:

        result = notifier.send_photo("/does/not/exist.png")

        assert result is None
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

        deadline = time.time() + 2
        while not call_thread_names and time.time() < deadline:
            time.sleep(0.01)

    assert call_thread_names, "arka plan thread hic cagrilmadi"
    assert call_thread_names[0] != main_thread_name


def test_send_message_async_invokes_on_sent_callback_with_message_id():

    notifier = TelegramNotifier("token", "chat")

    received = []

    with patch(
        "modules.core.telegram_notifier.requests.post",
        return_value=_fake_response(ok=True, message_id=777)
    ):

        notifier.send_message_async(
            "merhaba", on_sent=lambda message_id: received.append(message_id)
        )

        deadline = time.time() + 2
        while not received and time.time() < deadline:
            time.sleep(0.01)

    assert received == [777]


def test_send_contact_request_success_returns_message_id():

    notifier = TelegramNotifier("token", "chat")

    with patch(
        "modules.core.telegram_notifier.requests.post",
        return_value=_fake_response(ok=True, message_id=55)
    ) as mock_post:

        result = notifier.send_contact_request("Lütfen numaranızı paylaşın")

        assert result == 55

        args, kwargs = mock_post.call_args
        assert "sendMessage" in args[0]
        assert kwargs["data"]["chat_id"] == "chat"

        import json
        markup = json.loads(kwargs["data"]["reply_markup"])
        assert markup["keyboard"][0][0]["request_contact"] is True


def test_send_contact_request_not_configured_skips_network_call():

    notifier = TelegramNotifier("", "")

    with patch(
        "modules.core.telegram_notifier.requests.post"
    ) as mock_post:

        result = notifier.send_contact_request("merhaba")

        assert result is None
        assert not mock_post.called


def test_send_contact_request_network_exception_does_not_raise():

    notifier = TelegramNotifier("token", "chat")

    with patch(
        "modules.core.telegram_notifier.requests.post",
        side_effect=ConnectionError("no internet")
    ):

        assert notifier.send_contact_request("merhaba") is None


def test_send_photo_async_invokes_on_sent_callback_with_none_on_failure(tmp_path):

    image_path = tmp_path / "ng.png"
    image_path.write_bytes(b"fake png bytes")

    notifier = TelegramNotifier("token", "chat")

    received = []

    with patch(
        "modules.core.telegram_notifier.requests.post",
        return_value=_fake_response(ok=False, status_code=500)
    ):

        notifier.send_photo_async(
            str(image_path),
            on_sent=lambda message_id: received.append(message_id)
        )

        deadline = time.time() + 2
        while not received and time.time() < deadline:
            time.sleep(0.01)

    assert received == [None]
