import json
import threading
from dataclasses import dataclass, asdict
from pathlib import Path

from modules.utils.logger import get_logger

app_logger = get_logger()


@dataclass(slots=True)
class QueuedNotification:
    kind: str  # "message" ya da "photo"
    bot_token: str
    chat_id: str
    text: str = ""
    image_path: str = ""
    record_id: int = None
    is_primary: bool = False


class TelegramNotificationQueue:
    """
    Ağ/Telegram erişilemediği için gönderilemeyen bildirimleri diske
    kaydedip bağlantı geri geldiğinde tekrar göndermeyi dener.

    Bu sınıf olmadan, InspectionUIController bir NG/bağlantı-kopması
    bildirimini göndermeyi dener, başarısız olur ve bildirim
    sessizce kaybolurdu - operatör internet kesintisi sırasında
    oluşan NG'lerden hiç haberdar olmazdı.
    """

    def __init__(self, path="configuration/telegram_queue.json"):

        self.path = Path(path)
        self._lock = threading.Lock()

    # -------------------------------------------------

    def load(self) -> list:

        if not self.path.exists():
            return []

        try:

            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)

            return [
                QueuedNotification(**item)
                for item in data.get("items", [])
            ]

        except Exception as e:

            app_logger.warning(
                "Telegram bildirim kuyruğu okunamadı: %s", e
            )

            return []

    # -------------------------------------------------

    def _save(self, items: list):

        self.path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.path, "w", encoding="utf-8") as f:

            json.dump(
                {"items": [asdict(item) for item in items]},
                f,
                indent=4,
                ensure_ascii=False
            )

    # -------------------------------------------------

    def enqueue(self, item: QueuedNotification):

        with self._lock:

            items = self.load()
            items.append(item)
            self._save(items)

    # -------------------------------------------------

    def flush(self, notifier_factory, on_message_sent=None) -> int:
        """
        Kuyruktaki her öğeyi göndermeyi dener (SENKRON - ağ isteği
        içerir, her zaman arka plan thread'inden çağrılmalı).
        Başarısız kalanlar kuyrukta kalır. Başarıyla gönderilen
        bildirim sayısını döner.

        notifier_factory(bot_token, chat_id) -> TelegramNotifier
        on_message_sent(record_id, message_id) - sadece is_primary
        olan ve başarıyla giden öğeler için çağrılır (NG mesajına
        emoji tepkisiyle düzeltme yapılabilmesi için).
        """

        with self._lock:

            items = self.load()

            if not items:
                return 0

            remaining = []
            sent_count = 0

            for item in items:

                notifier = notifier_factory(item.bot_token, item.chat_id)

                message_id = self._send_one(notifier, item)

                if message_id is not None:

                    sent_count += 1

                    if item.is_primary and on_message_sent is not None:
                        on_message_sent(item.record_id, message_id)

                else:

                    remaining.append(item)

            self._save(remaining)

            return sent_count

    # -------------------------------------------------

    def _send_one(self, notifier, item: QueuedNotification):

        if item.kind in ("photo", "document"):

            if Path(item.image_path).exists():

                if item.kind == "photo":
                    return notifier.send_photo(item.image_path, caption=item.text)

                return notifier.send_document(item.image_path, caption=item.text)

            app_logger.warning(
                "Kuyruktaki %s dosyası artık bulunamıyor, sadece metin "
                "gönderiliyor: %s",
                item.kind,
                item.image_path
            )

        return notifier.send_message(item.text)
