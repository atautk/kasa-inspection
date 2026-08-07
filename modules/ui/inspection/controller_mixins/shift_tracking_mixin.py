from datetime import datetime, timezone

from modules.core.telegram_notifier import TelegramNotifier


class ShiftTrackingMixin:
    """
    Vardiya bazlı üretim takibi: bandın vardiya hedefi tanımlıysa
    (shift_target_count > 0), vardiya başlangıcından bu yana kaç
    kasa incelendiğini hesaplar, arayüzde gösterir ve beklenen
    tempoya göre ciddi şekilde geride kalınmışsa Telegram'dan uyarır.
    Chat id / retry-callback için TelegramMixin'e bağımlıdır.
    """

    SHIFT_CHECK_INTERVAL_SECONDS = 60.0
    SHIFT_PACE_TOLERANCE = 0.2
    SHIFT_WARNING_COOLDOWN_SECONDS = 3600.0

    def _maybe_check_shift_progress(self):

        if not self._throttled(
            "_last_shift_check_attempt",
            self.SHIFT_CHECK_INTERVAL_SECONDS
        ):
            return

        if self.current_band is None or self.inspection_logger is None:
            return

        if self.shift_start_time is None:
            return

        target = self.current_band.shift_target_count

        if target <= 0:
            self.page.set_shift_progress(None)
            return

        duration_hours = self.current_band.shift_duration_hours

        now_utc = datetime.now(timezone.utc)

        elapsed_hours = (
            (now_utc - self.shift_start_time).total_seconds() / 3600
        )

        stats = self.inspection_logger.compute_period_stats(
            self.shift_start_time.isoformat()
        )
        produced = stats["total"]

        self.page.set_shift_progress({
            "produced": produced,
            "target": target,
            "elapsed_hours": elapsed_hours,
            "duration_hours": duration_hours
        })

        if duration_hours <= 0:
            return

        elapsed_fraction = min(elapsed_hours / duration_hours, 1.0)
        expected_by_now = target * elapsed_fraction

        is_behind = produced < expected_by_now * (1 - self.SHIFT_PACE_TOLERANCE)

        if not is_behind:
            return

        if not self._cooldown_ready(
            "_last_shift_warning_at", self.SHIFT_WARNING_COOLDOWN_SECONDS
        ):
            return

        self._notify_shift_behind_pace(produced, target, expected_by_now)

    def _notify_shift_behind_pace(self, produced, target, expected_by_now):

        settings = self.telegram_settings_manager.load()

        if not settings.is_configured():
            return

        band_name = (
            self.current_band.name
            if self.current_band is not None
            else "?"
        )

        text = (
            f"⏱ Vardiya hedefinin gerisinde - {band_name}\n"
            f"Üretim: {produced} / {target} "
            f"(bu saatte beklenen: ~{int(expected_by_now)})"
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
