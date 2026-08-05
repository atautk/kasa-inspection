from dataclasses import dataclass


@dataclass(slots=True)
class TelegramSettings:

    bot_token: str = ""
    chat_id: str = ""

    notify_on_ng: bool = True
    notify_on_disconnect: bool = True

    # NG bildirimine bu emoji ile tepki verilirse kayıt otomatik
    # olarak "incelendi/OK" yapılır (yanlış tespit düzeltmesiyle
    # aynı mantık, orijinal sonuç korunur).
    confirm_emoji: str = "✅"
    react_to_confirm: bool = False

    def is_configured(self) -> bool:

        return bool(self.bot_token.strip()) and bool(self.chat_id.strip())
