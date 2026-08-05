import time
from unittest.mock import patch, MagicMock

from modules.core.telegram_reaction_poller import TelegramReactionPoller


def _fake_updates_response(updates, ok=True, status_code=200):

    response = MagicMock()
    response.ok = ok
    response.status_code = status_code
    response.json.return_value = {"result": updates}

    return response


def test_start_and_stop_run_flag():

    poller = TelegramReactionPoller("token", on_reaction=lambda *a: None)

    assert poller.is_running() is False

    with patch("modules.core.telegram_reaction_poller.requests.get"):

        poller.start()
        assert poller.is_running() is True

        poller.stop()

        # thread'in dongusunu bitirmesi icin kisa bir sure ver
        deadline = time.time() + 2
        while poller._thread.is_alive() and time.time() < deadline:
            time.sleep(0.01)

    assert poller.is_running() is False


def test_starting_twice_does_not_spawn_second_thread():

    poller = TelegramReactionPoller("token", on_reaction=lambda *a: None)

    with patch("modules.core.telegram_reaction_poller.requests.get"):

        poller.start()
        first_thread = poller._thread

        poller.start()

        assert poller._thread is first_thread

        poller.stop()


def test_handle_update_calls_on_reaction_for_emoji_reactions():

    received = []

    poller = TelegramReactionPoller(
        "token", on_reaction=lambda message_id, emoji: received.append(
            (message_id, emoji)
        )
    )

    update = {
        "update_id": 1,
        "message_reaction": {
            "message_id": 555,
            "new_reaction": [{"type": "emoji", "emoji": "✅"}]
        }
    }

    poller._handle_update(update)

    assert received == [(555, "✅")]


def test_handle_update_ignores_non_reaction_updates():

    received = []

    poller = TelegramReactionPoller(
        "token", on_reaction=lambda *a: received.append(a)
    )

    poller._handle_update({"update_id": 1, "message": {"text": "hello"}})

    assert received == []


def test_handle_update_ignores_non_emoji_reaction_types():

    received = []

    poller = TelegramReactionPoller(
        "token", on_reaction=lambda *a: received.append(a)
    )

    update = {
        "update_id": 1,
        "message_reaction": {
            "message_id": 555,
            "new_reaction": [{"type": "custom_emoji", "custom_emoji_id": "x"}]
        }
    }

    poller._handle_update(update)

    assert received == []


def test_poll_once_updates_offset_and_dispatches():

    received = []

    poller = TelegramReactionPoller(
        "token", on_reaction=lambda *a: received.append(a)
    )
    poller._running = True

    updates = [
        {
            "update_id": 10,
            "message_reaction": {
                "message_id": 1,
                "new_reaction": [{"type": "emoji", "emoji": "👍"}]
            }
        },
        {
            "update_id": 11,
            "message_reaction": {
                "message_id": 2,
                "new_reaction": [{"type": "emoji", "emoji": "✅"}]
            }
        }
    ]

    with patch(
        "modules.core.telegram_reaction_poller.requests.get",
        return_value=_fake_updates_response(updates)
    ) as mock_get:

        poller._poll_once()

        assert mock_get.call_args.kwargs["params"]["timeout"] == \
            poller.POLL_TIMEOUT_SECONDS
        assert "offset" not in mock_get.call_args.kwargs["params"]

    assert poller._offset == 12
    assert received == [(1, "👍"), (2, "✅")]


def test_poll_once_sends_offset_on_subsequent_calls():

    poller = TelegramReactionPoller("token", on_reaction=lambda *a: None)
    poller._running = True
    poller._offset = 50

    with patch(
        "modules.core.telegram_reaction_poller.requests.get",
        return_value=_fake_updates_response([])
    ) as mock_get:

        poller._poll_once()

        assert mock_get.call_args.kwargs["params"]["offset"] == 50


def test_poll_once_failure_response_does_not_raise():

    poller = TelegramReactionPoller("token", on_reaction=lambda *a: None)
    poller._running = True

    with patch(
        "modules.core.telegram_reaction_poller.requests.get",
        return_value=_fake_updates_response([], ok=False, status_code=500)
    ):

        poller._poll_once()  # exception firlatmamali


def test_allowed_update_types_only_includes_provided_callbacks():

    only_reaction = TelegramReactionPoller("token", on_reaction=lambda *a: None)
    assert only_reaction._allowed_update_types() == ["message_reaction"]

    only_message = TelegramReactionPoller("token", on_message=lambda u: None)
    assert only_message._allowed_update_types() == ["message"]

    both = TelegramReactionPoller(
        "token", on_reaction=lambda *a: None, on_message=lambda u: None
    )
    assert both._allowed_update_types() == ["message_reaction", "message"]

    neither = TelegramReactionPoller("token")
    assert neither._allowed_update_types() == []


def test_handle_update_dispatches_message_updates_to_on_message():

    received = []

    poller = TelegramReactionPoller(
        "token", on_message=lambda msg: received.append(msg)
    )

    update = {
        "update_id": 1,
        "message": {
            "chat": {"id": 123},
            "contact": {"phone_number": "+90555", "first_name": "Ahmet"}
        }
    }

    poller._handle_update(update)

    assert received == [update["message"]]


def test_handle_update_without_on_message_ignores_message_updates():

    poller = TelegramReactionPoller("token", on_reaction=lambda *a: None)

    # on_message verilmedigi icin message update'i sessizce yok sayilmali,
    # hata firlatmamali
    poller._handle_update({"update_id": 1, "message": {"text": "hi"}})


def test_handle_update_prefers_reaction_over_message_when_both_given():

    reactions_received = []
    messages_received = []

    poller = TelegramReactionPoller(
        "token",
        on_reaction=lambda mid, emoji: reactions_received.append((mid, emoji)),
        on_message=lambda msg: messages_received.append(msg)
    )

    update = {
        "update_id": 1,
        "message_reaction": {
            "message_id": 5,
            "new_reaction": [{"type": "emoji", "emoji": "✅"}]
        }
    }

    poller._handle_update(update)

    assert reactions_received == [(5, "✅")]
    assert messages_received == []
