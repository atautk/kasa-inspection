import pytest

from modules.configuration.telegram_settings import TelegramSettings
from modules.configuration.telegram_settings_manager import (
    TelegramSettingsManager
)


@pytest.fixture
def manager(tmp_path):

    return TelegramSettingsManager(path=tmp_path / "telegram_settings.json")


def test_default_settings_when_no_file_exists(manager):

    settings = manager.load()

    assert settings.bot_token == ""
    assert settings.chat_id == ""
    assert settings.notify_on_ng is True
    assert settings.notify_on_disconnect is True
    assert settings.is_configured() is False


def test_save_and_load_roundtrip(manager):

    settings = TelegramSettings(
        bot_token="123:ABC",
        chat_id="456",
        notify_on_ng=False,
        notify_on_disconnect=True
    )

    manager.save(settings)

    reloaded = manager.load()

    assert reloaded.bot_token == "123:ABC"
    assert reloaded.chat_id == "456"
    assert reloaded.notify_on_ng is False
    assert reloaded.notify_on_disconnect is True
    assert reloaded.is_configured() is True


def test_corrupt_file_falls_back_to_defaults(manager):

    manager.path.parent.mkdir(parents=True, exist_ok=True)
    manager.path.write_text("not valid json", encoding="utf-8")

    settings = manager.load()

    assert settings.bot_token == ""
    assert settings.is_configured() is False


def test_is_configured_requires_both_token_and_chat_id():

    assert TelegramSettings(bot_token="x", chat_id="").is_configured() is False
    assert TelegramSettings(bot_token="", chat_id="y").is_configured() is False
    assert TelegramSettings(bot_token="x", chat_id="y").is_configured() is True
    assert TelegramSettings(bot_token="  ", chat_id="y").is_configured() is False
