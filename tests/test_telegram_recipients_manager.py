import pytest

from modules.configuration.telegram_recipient import TelegramRecipient
from modules.configuration.telegram_recipients_manager import (
    TelegramRecipientsManager
)


@pytest.fixture
def manager(tmp_path):

    return TelegramRecipientsManager(
        path=tmp_path / "telegram_recipients.json"
    )


def test_empty_when_no_file_exists(manager):

    assert manager.load() == []


def test_register_new_recipient(manager):

    recipient = manager.register("+905551112233", "chat1", "Ahmet")

    assert recipient.phone_number == "+905551112233"
    assert recipient.chat_id == "chat1"
    assert recipient.display_name == "Ahmet"
    assert recipient.active is True

    loaded = manager.load()
    assert len(loaded) == 1
    assert loaded[0].phone_number == "+905551112233"


def test_register_existing_phone_number_updates_chat_id(manager):

    manager.register("+905551112233", "old_chat", "Ahmet")
    manager.register("+905551112233", "new_chat", "Ahmet Yılmaz")

    loaded = manager.load()

    assert len(loaded) == 1
    assert loaded[0].chat_id == "new_chat"
    assert loaded[0].display_name == "Ahmet Yılmaz"


def test_register_existing_recipient_preserves_active_state(manager):

    manager.register("+905551112233", "chat1", "Ahmet")
    manager.set_active("+905551112233", False)

    manager.register("+905551112233", "chat2", "Ahmet")

    loaded = manager.load()
    assert loaded[0].active is False


def test_set_active_toggles_flag(manager):

    manager.register("+905551112233", "chat1", "Ahmet")

    manager.set_active("+905551112233", False)
    assert manager.load()[0].active is False

    manager.set_active("+905551112233", True)
    assert manager.load()[0].active is True


def test_set_active_unknown_phone_raises(manager):

    with pytest.raises(ValueError):
        manager.set_active("+90000", True)


def test_remove_recipient(manager):

    manager.register("+905551112233", "chat1", "Ahmet")
    manager.register("+905559998877", "chat2", "Mehmet")

    manager.remove("+905551112233")

    loaded = manager.load()
    assert len(loaded) == 1
    assert loaded[0].phone_number == "+905559998877"


def test_remove_unknown_phone_does_not_raise(manager):

    manager.remove("+90000")


def test_active_chat_ids_only_includes_active_with_chat_id(manager):

    manager.register("+9055511", "chat1", "Ahmet")
    manager.register("+9055522", "chat2", "Mehmet")
    manager.register("+9055533", "", "Boş Chat")

    manager.set_active("+9055522", False)

    assert manager.active_chat_ids() == ["chat1"]


def test_corrupt_file_falls_back_to_empty_list(manager):

    manager.path.parent.mkdir(parents=True, exist_ok=True)
    manager.path.write_text("not valid json", encoding="utf-8")

    assert manager.load() == []


def test_save_and_load_roundtrip_multiple_recipients(manager):

    recipients = [
        TelegramRecipient("+9055511", "chat1", "Ahmet", True),
        TelegramRecipient("+9055522", "chat2", "Mehmet", False)
    ]

    manager.save(recipients)

    loaded = manager.load()

    assert len(loaded) == 2
    assert loaded[0].display_name == "Ahmet"
    assert loaded[1].active is False
