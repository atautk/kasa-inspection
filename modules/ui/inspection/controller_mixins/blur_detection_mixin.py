from modules.core.telegram_notifier import TelegramNotifier


class BlurDetectionMixin:
    """
    Kameradan gelen görüntünün net olup olmadığını periyodik olarak
    kontrol eder (Laplacian varyansı - bkz. BlurDetector). Tek bir
    kötü kare (ör. kasa hareket ederken oluşan geçici bulanıklık)
    uyarı tetiklemez; BLUR_STREAK_THRESHOLD kadar ARDIŞIK kontrolde
    de bulanık çıkarsa (sürekli bir durum - lens kirli, odak kaymış)
    arayüzde ve Telegram'da bildirilir. Chat id / retry-callback için
    TelegramMixin'e bağımlıdır.
    """

    BLUR_CHECK_INTERVAL_SECONDS = 2.0
    BLUR_STREAK_THRESHOLD = 3
    BLUR_WARNING_COOLDOWN_SECONDS = 300.0

    def _maybe_check_blur(self, frame):

        if not self._throttled(
            "_last_blur_check_attempt", self.BLUR_CHECK_INTERVAL_SECONDS
        ):
            return

        if self.current_band is None:
            return

        sharpness = self.blur_detector.compute_sharpness(frame)

        if self.debug_dialog is not None:
            self.debug_dialog.set_current_sharpness(sharpness)

        is_blurry = sharpness < self.current_band.blur_threshold

        if is_blurry:
            self.blur_streak += 1
        else:
            self.blur_streak = 0
            self.page.hide_blur_warning()
            return

        if self.blur_streak < self.BLUR_STREAK_THRESHOLD:
            return

        self.page.show_blur_warning(sharpness)

        if not self._cooldown_ready(
            "_last_blur_warning_at", self.BLUR_WARNING_COOLDOWN_SECONDS
        ):
            return

        self._notify_blur_detected(sharpness)

    def _notify_blur_detected(self, sharpness):

        settings = self.telegram_settings_manager.load()

        if not settings.is_configured():
            return

        band_name = (
            self.current_band.name
            if self.current_band is not None
            else "?"
        )

        text = (
            f"📷 Kamera görüntüsü bulanık görünüyor - {band_name}\n"
            f"Netlik: {sharpness:.1f} (eşik: "
            f"{self.current_band.blur_threshold:.1f}). Lens kirli/"
            f"buğulu olabilir ya da odak kaymış olabilir."
        )

        chat_ids = self._telegram_chat_ids(settings.chat_id)

        for chat_id in chat_ids:

            callback = self._telegram_retry_on_failure_callback(
                kind="message",
                bot_token=settings.bot_token,
                chat_id=chat_id,
                text=text
            )

            TelegramNotifier(settings.bot_token, chat_id).send_message_async(
                text, on_sent=callback
            )
