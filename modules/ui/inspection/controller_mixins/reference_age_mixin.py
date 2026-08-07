import time

from modules.core.telegram_notifier import TelegramNotifier


class ReferenceAgeMixin:
    """
    Işık/kamera koşulları zamanla kayabileceğinden, referans fotoğrafı
    (dosyanın son değiştirilme tarihinden bu yana)
    band.reference_max_age_days'ten daha eskiyse hatırlatır. Birincil
    kameranın yanı sıra varsa ek kamera kanallarının referansları da
    kontrol edilir. Chat id / retry-callback için TelegramMixin'e
    bağımlıdır.
    """

    REFERENCE_AGE_CHECK_INTERVAL_SECONDS = 3600.0
    REFERENCE_AGE_WARNING_COOLDOWN_SECONDS = 86400.0

    def _maybe_check_reference_age(self):

        if not self._throttled(
            "_last_reference_age_check_attempt",
            self.REFERENCE_AGE_CHECK_INTERVAL_SECONDS
        ):
            return

        if self.current_band is None:
            return

        max_age_days = self.current_band.reference_max_age_days

        if max_age_days <= 0:
            self.page.hide_reference_age_warning()
            return

        stale_channels = self._find_stale_reference_channels(max_age_days)

        if not stale_channels:
            self.page.hide_reference_age_warning()
            return

        self.page.show_reference_age_warning(
            f"Referans fotoğrafı eski görünüyor ({max_age_days}+ gün): "
            f"{', '.join(stale_channels)}"
        )

        if not self._cooldown_ready(
            "_last_reference_age_warning_at",
            self.REFERENCE_AGE_WARNING_COOLDOWN_SECONDS
        ):
            return

        self._notify_reference_age(stale_channels, max_age_days)

    def _find_stale_reference_channels(self, max_age_days) -> list:

        stale = []

        if self._is_reference_stale(self.current_band.reference, max_age_days):
            stale.append("Birincil")

        for channel in self.current_band.cameras:

            if self._is_reference_stale(channel.reference, max_age_days):
                stale.append(channel.name)

        return stale

    def _is_reference_stale(self, reference_path, max_age_days) -> bool:

        if not reference_path.exists():
            return False

        age_seconds = time.time() - reference_path.stat().st_mtime

        return age_seconds >= max_age_days * 86400

    def _notify_reference_age(self, stale_channels, max_age_days):

        settings = self.telegram_settings_manager.load()

        if not settings.is_configured():
            return

        band_name = (
            self.current_band.name
            if self.current_band is not None
            else "?"
        )

        text = (
            f"🕒 Referans fotoğrafı eskimiş - {band_name}\n"
            f"{max_age_days}+ gündür yenilenmedi: "
            f"{', '.join(stale_channels)}\n"
            "Işık/kamera koşulları değiştiyse referansı yenilemeyi "
            "düşünün."
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
