import threading

import requests

from modules.utils.logger import get_logger

app_logger = get_logger()


class TelegramNotifier:
    """
    Telegram Bot API üzerinden mesaj/fotoğraf gönderir.

    Ağ isteği birkaç saniye sürebileceğinden ve bu uygulamada
    inceleme döngüsü ana arayüz thread'inde çalıştığından, gönderim
    ~her zaman send_*_async() ile arka plan thread'inde tetiklenmeli
    - aksi halde yavaş/kopuk bir internet bağlantısı arayüzü dondurur.

    Ağ/ayar sorunlarında uygulamayı ÇÖKERTMEZ; hata sessizce loglanır
    (Arduino ile aynı felsefe: dış donanım/servis her zaman
    güvenilmez kabul edilir).
    """

    TIMEOUT_SECONDS = 5

    def __init__(self, bot_token: str, chat_id: str):

        self.bot_token = bot_token
        self.chat_id = chat_id

    # -------------------------------------------------

    def is_configured(self) -> bool:

        return (
            bool(self.bot_token.strip())
            and bool(self.chat_id.strip())
        )

    # -------------------------------------------------
    # Senkron Gönderim (test edilebilir, sonuç bekler)
    # -------------------------------------------------
    #
    # Başarılıysa gönderilen mesajın Telegram mesaj id'sini (int),
    # başarısızsa None döner. Mesaj id'si, kullanıcı NG mesajına
    # emoji ile tepki verdiğinde hangi kaydın düzeltileceğini bulmak
    # için saklanır (bkz. InspectionLogger.set_telegram_message_id).

    def send_message(self, text: str):

        if not self.is_configured():
            return None

        try:

            response = requests.post(
                f"https://api.telegram.org/bot{self.bot_token}"
                f"/sendMessage",
                data={"chat_id": self.chat_id, "text": text},
                timeout=self.TIMEOUT_SECONDS
            )

            return self._extract_message_id(response, "mesaj")

        except Exception as e:

            app_logger.warning(
                "Telegram mesajı gönderilemedi: %s", e
            )

            return None

    def send_photo(self, image_path: str, caption: str = ""):

        if not self.is_configured():
            return None

        try:

            with open(image_path, "rb") as f:

                response = requests.post(
                    f"https://api.telegram.org/bot{self.bot_token}"
                    f"/sendPhoto",
                    data={"chat_id": self.chat_id, "caption": caption},
                    files={"photo": f},
                    timeout=self.TIMEOUT_SECONDS
                )

            return self._extract_message_id(response, "fotoğraf")

        except Exception as e:

            app_logger.warning(
                "Telegram fotoğrafı gönderilemedi: %s", e
            )

            return None

    # -------------------------------------------------

    def _extract_message_id(self, response, label: str):

        if not response.ok:

            app_logger.warning(
                "Telegram %s gönderilemedi (HTTP %s): %s",
                label,
                response.status_code,
                response.text[:200]
            )

            return None

        try:

            return response.json()["result"]["message_id"]

        except Exception:

            return None

    # -------------------------------------------------
    # Asenkron Gönderim (canlı inceleme döngüsünde kullanılır)
    # -------------------------------------------------
    #
    # on_sent, verilirse gönderim tamamlandığında (arka plan
    # thread'inde) message_id (int) veya None ile çağrılır.

    def send_message_async(self, text: str, on_sent=None):

        def _run():

            message_id = self.send_message(text)

            if on_sent is not None:
                on_sent(message_id)

        threading.Thread(target=_run, daemon=True).start()

    def send_photo_async(self, image_path: str, caption: str = "", on_sent=None):

        def _run():

            message_id = self.send_photo(image_path, caption)

            if on_sent is not None:
                on_sent(message_id)

        threading.Thread(target=_run, daemon=True).start()
