from __future__ import annotations

import json
from pathlib import Path

from .telegram_recipient import TelegramRecipient


class TelegramRecipientsManager:
    """
    Botla eşleşip (numarasını paylaşıp) kaydolmuş kişilerin listesini
    diskte saklar. chat_id kişisel/kimlik bilgisi olduğu için
    operators.json/telegram_settings.json ile aynı mantıkla git'e
    girmeyen ayrı bir dosyada (configuration/telegram_recipients.json)
    saklanır.
    """

    def __init__(
        self,
        path: Path | str = "configuration/telegram_recipients.json"
    ):

        self.path = Path(path)

    # -------------------------------------------------

    def load(self) -> list[TelegramRecipient]:

        if not self.path.exists():
            return []

        try:

            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)

        except Exception:

            return []

        return [
            TelegramRecipient(
                phone_number=entry.get("phone_number", ""),
                chat_id=entry.get("chat_id", ""),
                display_name=entry.get("display_name", ""),
                active=entry.get("active", True)
            )
            for entry in data.get("recipients", [])
        ]

    # -------------------------------------------------

    def save(self, recipients: list[TelegramRecipient]):

        self.path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "recipients": [
                {
                    "phone_number": r.phone_number,
                    "chat_id": r.chat_id,
                    "display_name": r.display_name,
                    "active": r.active
                }
                for r in recipients
            ]
        }

        with open(self.path, "w", encoding="utf-8") as f:

            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )

    # -------------------------------------------------
    # Kayıt / Güncelleme
    # -------------------------------------------------

    def register(
        self,
        phone_number: str,
        chat_id: str,
        display_name: str = ""
    ) -> TelegramRecipient:
        """
        Bir numarayı ekler; aynı numara zaten kayıtlıysa (yeniden
        eşleştirme, isim değişikliği vb.) günceller - aktif/pasif
        durumunu korur.
        """

        recipients = self.load()

        for recipient in recipients:

            if recipient.phone_number == phone_number:

                recipient.chat_id = chat_id

                if display_name:
                    recipient.display_name = display_name

                self.save(recipients)

                return recipient

        new_recipient = TelegramRecipient(
            phone_number=phone_number,
            chat_id=chat_id,
            display_name=display_name,
            active=True
        )

        recipients.append(new_recipient)

        self.save(recipients)

        return new_recipient

    def set_active(self, phone_number: str, active: bool):

        recipients = self.load()

        for recipient in recipients:

            if recipient.phone_number == phone_number:

                recipient.active = active

                self.save(recipients)

                return

        raise ValueError(f"'{phone_number}' bulunamadı.")

    def remove(self, phone_number: str):

        recipients = [
            r for r in self.load()
            if r.phone_number != phone_number
        ]

        self.save(recipients)

    # -------------------------------------------------

    def active_chat_ids(self) -> list[str]:

        return [
            r.chat_id
            for r in self.load()
            if r.active and r.chat_id.strip()
        ]
