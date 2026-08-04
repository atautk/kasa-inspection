from dataclasses import dataclass


@dataclass(slots=True)
class TelegramSettings:

    bot_token: str = ""
    chat_id: str = ""

    notify_on_ng: bool = True
    notify_on_disconnect: bool = True

    def is_configured(self) -> bool:

        return bool(self.bot_token.strip()) and bool(self.chat_id.strip())
