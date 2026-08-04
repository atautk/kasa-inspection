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

    def send_message(self, text: str) -> bool:

        if not self.is_configured():
            return False

        try:

            response = requests.post(
                f"https://api.telegram.org/bot{self.bot_token}"
                f"/sendMessage",
                data={"chat_id": self.chat_id, "text": text},
                timeout=self.TIMEOUT_SECONDS
            )

            if not response.ok:

                app_logger.warning(
                    "Telegram mesajı gönderilemedi (HTTP %s): %s",
                    response.status_code,
                    response.text[:200]
                )

            return response.ok

        except Exception as e:

            app_logger.warning(
                "Telegram mesajı gönderilemedi: %s", e
            )

            return False

    def send_photo(self, image_path: str, caption: str = "") -> bool:

        if not self.is_configured():
            return False

        try:

            with open(image_path, "rb") as f:

                response = requests.post(
                    f"https://api.telegram.org/bot{self.bot_token}"
                    f"/sendPhoto",
                    data={"chat_id": self.chat_id, "caption": caption},
                    files={"photo": f},
                    timeout=self.TIMEOUT_SECONDS
                )

            if not response.ok:

                app_logger.warning(
                    "Telegram fotoğrafı gönderilemedi (HTTP %s): %s",
                    response.status_code,
                    response.text[:200]
                )

            return response.ok

        except Exception as e:

            app_logger.warning(
                "Telegram fotoğrafı gönderilemedi: %s", e
            )

            return False

    # -------------------------------------------------
    # Asenkron Gönderim (canlı inceleme döngüsünde kullanılır)
    # -------------------------------------------------

    def send_message_async(self, text: str):

        threading.Thread(
            target=self.send_message,
            args=(text,),
            daemon=True
        ).start()

    def send_photo_async(self, image_path: str, caption: str = ""):

        threading.Thread(
            target=self.send_photo,
            args=(image_path, caption),
            daemon=True
        ).start()
