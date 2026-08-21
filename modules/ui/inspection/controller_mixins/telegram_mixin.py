import threading

from modules.core.telegram_notifier import TelegramNotifier
from modules.core.telegram_reaction_poller import TelegramReactionPoller
from modules.core.telegram_notification_queue import QueuedNotification
from modules.utils.logger import get_logger

app_logger = get_logger()


class TelegramMixin:
    """
    Telegram bildirim gönderiminin ortak parçaları: alıcı listesi
    kurma, gönderim başarısız olursa kuyruğa ekleme (retry callback),
    NG/bağlantı-koptu bildirimleri, kuyruğu boşaltma ve emoji-tepki
    ile NG->OK düzeltme (reaction poller).

    Diğer özellik grupları (vardiya, bulanıklık, referans yaşı,
    tanınmayan kasa) kendi Telegram mesajlarını göndermek için bu
    mixin'in _telegram_chat_ids / _telegram_retry_on_failure_callback
    metodlarını yeniden kullanır.
    """

    TELEGRAM_QUEUE_FLUSH_INTERVAL_SECONDS = 60.0

    def _telegram_chat_ids(self, primary_chat_id: str) -> list:
        """
        Bildirimin gideceği tüm chat id'ler: birincil (ayarlardaki
        tek) chat + telefon numarasıyla kaydolmuş, aktif işaretli
        tüm alıcılar. Tekrarlar elenir.
        """

        chat_ids = []

        if primary_chat_id.strip():
            chat_ids.append(primary_chat_id.strip())

        for chat_id in self.telegram_recipients_manager.active_chat_ids():

            if chat_id not in chat_ids:
                chat_ids.append(chat_id)

        return chat_ids

    def _notify_telegram_ng(self, results: dict, image_path, record_id):

        settings = self.telegram_settings_manager.load()

        if not settings.notify_on_ng or not settings.bot_token.strip():
            return

        chat_ids = self._telegram_chat_ids(settings.chat_id)

        if not chat_ids:
            return

        ng_names = [
            name for name, data in results.items()
            if not data.get("ok", True)
        ]

        band_name = (
            self.current_band.name
            if self.current_band is not None
            else "?"
        )

        caption = (
            f"⚠ HATA - {band_name}\n"
            f"Hatalı gözler: {', '.join(ng_names) if ng_names else '-'}"
        )

        if settings.react_to_confirm:

            caption += (
                f"\n\nYanlış tespitse bu mesaja {settings.confirm_emoji} "
                "ile tepki verin, otomatik olarak UYGUN'a çevrilir."
            )

        # inspection_logger band değişse bile DOĞRU kayda yazsın diye
        # şu anki referansı closure içine sabitliyoruz (arka plan
        # thread'i mesaj gönderimi bitince çalışır, o ana kadar band
        # değişmiş/durdurulmuş olabilir).
        logger_at_send_time = self.inspection_logger

        def on_primary_success(message_id):

            # Emoji ile onaylama sadece BİRİNCİL sohbetteki mesaj
            # için destekleniyor (her alıcının kendi mesaj id'sini
            # ayrı ayrı izlemek şimdilik kapsam dışı).
            if record_id is not None and logger_at_send_time is not None:
                logger_at_send_time.set_telegram_message_id(
                    record_id, message_id
                )

        for index, chat_id in enumerate(chat_ids):

            notifier = TelegramNotifier(settings.bot_token, chat_id)

            is_primary = index == 0

            callback = self._telegram_retry_on_failure_callback(
                kind="photo" if image_path else "message",
                bot_token=settings.bot_token,
                chat_id=chat_id,
                text=caption,
                image_path=str(image_path) if image_path else "",
                record_id=record_id,
                is_primary=is_primary,
                on_success=on_primary_success if is_primary else None
            )

            if image_path:
                notifier.send_photo_async(
                    image_path, caption=caption, on_sent=callback
                )
            else:
                notifier.send_message_async(caption, on_sent=callback)

    def _telegram_retry_on_failure_callback(
        self,
        kind,
        bot_token,
        chat_id,
        text,
        image_path="",
        record_id=None,
        is_primary=False,
        on_success=None
    ):
        """
        Gönderim başarılıysa (varsa) on_success(message_id) çağırır.
        Başarısızsa - ağ/Telegram erişilemiyorsa - bildirimi kuyruğa
        ekler ki bağlantı geri geldiğinde tekrar denensin (bkz.
        _maybe_flush_telegram_queue).
        """

        def on_sent(message_id):

            if message_id is not None:

                if on_success is not None:
                    on_success(message_id)

                return

            self.telegram_queue.enqueue(QueuedNotification(
                kind=kind,
                bot_token=bot_token,
                chat_id=chat_id,
                text=text,
                image_path=image_path,
                record_id=record_id,
                is_primary=is_primary
            ))

        return on_sent

    def _notify_telegram_disconnect(self, device_name: str):

        settings = self.telegram_settings_manager.load()

        if not settings.notify_on_disconnect or not settings.bot_token.strip():
            return

        chat_ids = self._telegram_chat_ids(settings.chat_id)

        if not chat_ids:
            return

        band_name = (
            self.current_band.name
            if self.current_band is not None
            else "?"
        )

        text = f"🔌 {device_name} bağlantısı koptu - {band_name}"

        for chat_id in chat_ids:

            callback = self._telegram_retry_on_failure_callback(
                kind="message",
                bot_token=settings.bot_token,
                chat_id=chat_id,
                text=text
            )

            TelegramNotifier(
                settings.bot_token, chat_id
            ).send_message_async(text, on_sent=callback)

    def _maybe_flush_telegram_queue(self):
        """
        Ağ/Telegram erişilemediği için kuyruğa düşmüş bildirimleri
        tekrar göndermeyi dener. Her karede değil, en fazla
        TELEGRAM_QUEUE_FLUSH_INTERVAL_SECONDS'te bir - aksi halde
        bağlantı koptuğunda Telegram'a saniyede onlarca istek atılır.
        Ağ isteği içerdiğinden her zaman arka plan thread'inde çalışır.
        """

        if not self._throttled(
            "_last_telegram_flush_attempt",
            self.TELEGRAM_QUEUE_FLUSH_INTERVAL_SECONDS
        ):
            return

        if (
            self._telegram_flush_thread is not None
            and self._telegram_flush_thread.is_alive()
        ):
            return

        logger_at_flush_time = self.inspection_logger

        def on_message_sent(record_id, message_id):

            if record_id is not None and logger_at_flush_time is not None:
                logger_at_flush_time.set_telegram_message_id(
                    record_id, message_id
                )

        def _run():

            sent_count = self.telegram_queue.flush(
                notifier_factory=TelegramNotifier,
                on_message_sent=on_message_sent
            )

            if sent_count:

                app_logger.info(
                    "Kuyruktaki %d Telegram bildirimi gönderildi.",
                    sent_count
                )

        self._telegram_flush_thread = threading.Thread(
            target=_run, daemon=True
        )
        self._telegram_flush_thread.start()

    def _start_telegram_reaction_poller(self):

        settings = self.telegram_settings_manager.load()

        if not settings.react_to_confirm or not settings.is_configured():
            return

        self.telegram_reaction_poller = TelegramReactionPoller(
            settings.bot_token,
            on_reaction=self._on_telegram_reaction
        )

        self.telegram_reaction_poller.start()

    def _stop_telegram_reaction_poller(self):

        if self.telegram_reaction_poller is not None:

            self.telegram_reaction_poller.stop()
            self.telegram_reaction_poller = None

    def _on_telegram_reaction(self, message_id: int, emoji: str):
        """
        TelegramReactionPoller'ın arka plan thread'inden çağrılır.
        Sadece veri/DB katmanına dokunur (thread-safe), Qt widget'larına
        DOKUNMAZ.
        """

        settings = self.telegram_settings_manager.load()

        if emoji != settings.confirm_emoji:
            return

        if self.inspection_logger is None:
            return

        record_id = self.inspection_logger.find_record_by_telegram_message_id(
            message_id
        )

        if record_id is None:
            return

        self.inspection_logger.mark_reviewed_ok(
            record_id,
            operator_name=f"Telegram ({emoji})"
        )

        app_logger.info(
            "[Telegram] #%s kaydı %s tepkisiyle OK'e çevrildi",
            record_id,
            emoji
        )
