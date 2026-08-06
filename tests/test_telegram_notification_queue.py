import json

from modules.core.telegram_notification_queue import (
    TelegramNotificationQueue,
    QueuedNotification
)


class _FakeNotifier:
    """
    TelegramNotifier'ın sendMessage/sendPhoto/sendDocument'ını taklit
    eder - gerçek ağ isteği atmaz. *_result None ise "gönderilemedi"
    (kuyrukta kalmalı) davranışını simüle eder.
    """

    def __init__(
        self, bot_token, chat_id,
        message_result=99, photo_result=99, document_result=99
    ):

        self.bot_token = bot_token
        self.chat_id = chat_id
        self.message_result = message_result
        self.photo_result = photo_result
        self.document_result = document_result
        self.sent_messages = []
        self.sent_photos = []
        self.sent_documents = []

    def send_message(self, text):

        self.sent_messages.append(text)
        return self.message_result

    def send_photo(self, image_path, caption=""):

        self.sent_photos.append((image_path, caption))
        return self.photo_result

    def send_document(self, file_path, caption=""):

        self.sent_documents.append((file_path, caption))
        return self.document_result


def _queue(tmp_path):

    return TelegramNotificationQueue(tmp_path / "telegram_queue.json")


def test_enqueue_and_load_roundtrip(tmp_path):

    queue = _queue(tmp_path)

    item = QueuedNotification(
        kind="message",
        bot_token="tok",
        chat_id="123",
        text="merhaba",
        record_id=5,
        is_primary=True
    )

    queue.enqueue(item)

    loaded = queue.load()

    assert len(loaded) == 1
    assert loaded[0] == item


def test_load_missing_file_returns_empty_list(tmp_path):

    queue = _queue(tmp_path)

    assert queue.load() == []


def test_load_corrupted_file_returns_empty_list(tmp_path):

    queue = _queue(tmp_path)
    queue.path.parent.mkdir(parents=True, exist_ok=True)
    queue.path.write_text("not valid json", encoding="utf-8")

    assert queue.load() == []


def test_flush_empty_queue_returns_zero(tmp_path):

    queue = _queue(tmp_path)

    sent = queue.flush(notifier_factory=_FakeNotifier)

    assert sent == 0


def test_flush_successful_message_removes_from_queue(tmp_path):

    queue = _queue(tmp_path)

    queue.enqueue(QueuedNotification(
        kind="message", bot_token="tok", chat_id="123", text="merhaba"
    ))

    sent = queue.flush(
        notifier_factory=lambda token, chat_id: _FakeNotifier(
            token, chat_id, message_result=77
        )
    )

    assert sent == 1
    assert queue.load() == []


def test_flush_failed_message_stays_in_queue(tmp_path):

    queue = _queue(tmp_path)

    item = QueuedNotification(
        kind="message", bot_token="tok", chat_id="123", text="merhaba"
    )
    queue.enqueue(item)

    sent = queue.flush(
        notifier_factory=lambda token, chat_id: _FakeNotifier(
            token, chat_id, message_result=None
        )
    )

    assert sent == 0
    assert queue.load() == [item]


def test_flush_calls_on_message_sent_only_for_primary(tmp_path):

    queue = _queue(tmp_path)

    queue.enqueue(QueuedNotification(
        kind="message", bot_token="tok", chat_id="primary",
        text="a", record_id=1, is_primary=True
    ))
    queue.enqueue(QueuedNotification(
        kind="message", bot_token="tok", chat_id="secondary",
        text="b", record_id=1, is_primary=False
    ))

    calls = []

    queue.flush(
        notifier_factory=lambda token, chat_id: _FakeNotifier(
            token, chat_id, message_result=55
        ),
        on_message_sent=lambda record_id, message_id: calls.append(
            (record_id, message_id)
        )
    )

    assert calls == [(1, 55)]


def test_flush_photo_falls_back_to_text_when_file_missing(tmp_path):

    queue = _queue(tmp_path)

    queue.enqueue(QueuedNotification(
        kind="photo",
        bot_token="tok",
        chat_id="123",
        text="caption metni",
        image_path=str(tmp_path / "does_not_exist.jpg")
    ))

    fake = {}

    def factory(token, chat_id):
        notifier = _FakeNotifier(token, chat_id, message_result=1, photo_result=1)
        fake["notifier"] = notifier
        return notifier

    sent = queue.flush(notifier_factory=factory)

    assert sent == 1
    assert fake["notifier"].sent_messages == ["caption metni"]
    assert fake["notifier"].sent_photos == []


def test_flush_photo_sends_photo_when_file_exists(tmp_path):

    queue = _queue(tmp_path)

    image_path = tmp_path / "ng.jpg"
    image_path.write_bytes(b"fake-image-bytes")

    queue.enqueue(QueuedNotification(
        kind="photo",
        bot_token="tok",
        chat_id="123",
        text="caption",
        image_path=str(image_path)
    ))

    fake = {}

    def factory(token, chat_id):
        notifier = _FakeNotifier(token, chat_id, message_result=1, photo_result=1)
        fake["notifier"] = notifier
        return notifier

    queue.flush(notifier_factory=factory)

    assert fake["notifier"].sent_photos == [(str(image_path), "caption")]
    assert fake["notifier"].sent_messages == []


def test_flush_mixed_success_and_failure(tmp_path):

    queue = _queue(tmp_path)

    queue.enqueue(QueuedNotification(
        kind="message", bot_token="tok", chat_id="ok-chat", text="ok"
    ))
    queue.enqueue(QueuedNotification(
        kind="message", bot_token="tok", chat_id="fail-chat", text="fail"
    ))

    def factory(token, chat_id):

        result = None if chat_id == "fail-chat" else 1

        return _FakeNotifier(token, chat_id, message_result=result)

    sent = queue.flush(notifier_factory=factory)

    assert sent == 1

    remaining = queue.load()
    assert len(remaining) == 1
    assert remaining[0].chat_id == "fail-chat"


def test_flush_document_sends_when_file_exists(tmp_path):

    queue = _queue(tmp_path)

    file_path = tmp_path / "rapor.xlsx"
    file_path.write_bytes(b"fake-xlsx-bytes")

    queue.enqueue(QueuedNotification(
        kind="document",
        bot_token="tok",
        chat_id="123",
        text="Günlük Özet",
        image_path=str(file_path)
    ))

    fake = {}

    def factory(token, chat_id):
        notifier = _FakeNotifier(token, chat_id, document_result=1)
        fake["notifier"] = notifier
        return notifier

    sent = queue.flush(notifier_factory=factory)

    assert sent == 1
    assert fake["notifier"].sent_documents == [(str(file_path), "Günlük Özet")]
    assert fake["notifier"].sent_messages == []


def test_flush_document_falls_back_to_text_when_file_missing(tmp_path):

    queue = _queue(tmp_path)

    queue.enqueue(QueuedNotification(
        kind="document",
        bot_token="tok",
        chat_id="123",
        text="Günlük Özet",
        image_path=str(tmp_path / "does_not_exist.xlsx")
    ))

    fake = {}

    def factory(token, chat_id):
        notifier = _FakeNotifier(token, chat_id, message_result=1)
        fake["notifier"] = notifier
        return notifier

    sent = queue.flush(notifier_factory=factory)

    assert sent == 1
    assert fake["notifier"].sent_messages == ["Günlük Özet"]
    assert fake["notifier"].sent_documents == []


def test_queue_file_is_valid_json_on_disk(tmp_path):

    queue = _queue(tmp_path)

    queue.enqueue(QueuedNotification(
        kind="message", bot_token="tok", chat_id="123", text="x"
    ))

    data = json.loads(queue.path.read_text(encoding="utf-8"))

    assert len(data["items"]) == 1
    assert data["items"][0]["chat_id"] == "123"
