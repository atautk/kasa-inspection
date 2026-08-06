from __future__ import annotations

import json
from pathlib import Path

from .telegram_settings import TelegramSettings


class TelegramSettingsManager:
    """
    Telegram bot ayarlarını (bot_token, chat_id, hangi olaylarda
    bildirim gönderileceği) diskte saklar. Bot token bir kimlik
    bilgisi olduğu için band.json gibi git'e giren bir dosyada değil,
    operators.json ile aynı mantıkla gizli tutulan ayrı bir dosyada
    (configuration/telegram_settings.json, .gitignore'da) saklanır.
    """

    def __init__(
        self, path: Path | str = "configuration/telegram_settings.json"
    ):

        self.path = Path(path)

    # -------------------------------------------------

    def load(self) -> TelegramSettings:

        if not self.path.exists():
            return TelegramSettings()

        try:

            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)

        except Exception:

            return TelegramSettings()

        default = TelegramSettings()

        return TelegramSettings(
            bot_token=data.get("bot_token", ""),
            chat_id=data.get("chat_id", ""),
            notify_on_ng=data.get("notify_on_ng", True),
            notify_on_disconnect=data.get("notify_on_disconnect", True),
            confirm_emoji=data.get("confirm_emoji", default.confirm_emoji),
            react_to_confirm=data.get("react_to_confirm", False),
            daily_report_enabled=data.get("daily_report_enabled", False),
            last_daily_report_sent_at=data.get(
                "last_daily_report_sent_at", ""
            )
        )

    # -------------------------------------------------

    def save(self, settings: TelegramSettings):

        self.path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "bot_token": settings.bot_token,
            "chat_id": settings.chat_id,
            "notify_on_ng": settings.notify_on_ng,
            "notify_on_disconnect": settings.notify_on_disconnect,
            "confirm_emoji": settings.confirm_emoji,
            "react_to_confirm": settings.react_to_confirm,
            "daily_report_enabled": settings.daily_report_enabled,
            "last_daily_report_sent_at": settings.last_daily_report_sent_at
        }

        with open(self.path, "w", encoding="utf-8") as f:

            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )
