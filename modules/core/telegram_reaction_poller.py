import json
import threading
import time

import requests

from modules.utils.logger import get_logger

app_logger = get_logger()


class TelegramReactionPoller:
    """
    Arka planda periyodik olarak Telegram'ın getUpdates API'sini
    yoklar. İki tür güncellemeyi dinleyebilir:

    - message_reaction: daha önce gönderilmiş bir mesaja emoji ile
      tepki verilmesi -> on_reaction(message_id, emoji).
    - message: bota gelen herhangi bir mesaj (özellikle "Kişimi
      Paylaş" ile gönderilen contact bilgisi) -> on_message(update).

    Hangi callback verilirse sadece o güncelleme türü Telegram'dan
    istenir (allowed_updates).

    Kendi arka plan thread'inde (uzun-poll ile) çalışır; ana arayüz
    thread'ini asla bloklamaz. Ağ hatalarında çökmez, bir süre
    bekleyip tekrar dener.
    """

    POLL_TIMEOUT_SECONDS = 20
    RETRY_DELAY_SECONDS = 5

    def __init__(self, bot_token: str, on_reaction=None, on_message=None):

        self.bot_token = bot_token
        self.on_reaction = on_reaction
        self.on_message = on_message

        self._offset = None
        self._running = False
        self._thread = None

    # -------------------------------------------------

    def start(self):

        if self._running:
            return

        self._running = True

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):

        self._running = False

    def is_running(self) -> bool:

        return self._running

    # -------------------------------------------------

    def _run(self):

        while self._running:

            try:

                self._poll_once()

            except Exception as e:

                app_logger.warning(
                    "Telegram reaksiyon yoklaması başarısız: %s", e
                )

                time.sleep(self.RETRY_DELAY_SECONDS)

    def _allowed_update_types(self) -> list:

        types = []

        if self.on_reaction is not None:
            types.append("message_reaction")

        if self.on_message is not None:
            types.append("message")

        return types

    def _poll_once(self):

        params = {
            "timeout": self.POLL_TIMEOUT_SECONDS,
            "allowed_updates": json.dumps(self._allowed_update_types())
        }

        if self._offset is not None:
            params["offset"] = self._offset

        response = requests.get(
            f"https://api.telegram.org/bot{self.bot_token}/getUpdates",
            params=params,
            timeout=self.POLL_TIMEOUT_SECONDS + 10
        )

        if not self._running:
            return

        if not response.ok:

            app_logger.warning(
                "Telegram getUpdates başarısız (HTTP %s)",
                response.status_code
            )

            time.sleep(self.RETRY_DELAY_SECONDS)

            return

        data = response.json()

        for update in data.get("result", []):

            self._offset = update["update_id"] + 1

            self._handle_update(update)

    def _handle_update(self, update: dict):

        reaction = update.get("message_reaction")

        if reaction is not None and self.on_reaction is not None:

            self._handle_reaction(reaction)

            return

        message = update.get("message")

        if message is not None and self.on_message is not None:

            self.on_message(message)

    def _handle_reaction(self, reaction: dict):

        message_id = reaction.get("message_id")

        if message_id is None:
            return

        for entry in reaction.get("new_reaction", []):

            if entry.get("type") == "emoji":

                self.on_reaction(message_id, entry.get("emoji"))
