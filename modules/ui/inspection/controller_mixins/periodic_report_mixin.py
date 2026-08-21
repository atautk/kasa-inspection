import threading
from datetime import datetime, timezone, timedelta

from modules.core.telegram_notifier import TelegramNotifier
from modules.core.telegram_notification_queue import QueuedNotification
from modules.configuration.periodic_report_exporter import (
    PeriodicReportExporter
)


class PeriodicReportMixin:
    """
    Ayarlarda açıksa, her REPORT_PERIOD_HOURS saatte bir bandın
    toplam/OK/NG ve model/ROI bazlı özetini bir Excel dosyası olarak
    Telegram'a gönderir. Gönderim başarısız olursa (ağ kopuksa) diğer
    bildirimlerle aynı kuyruğa (telegram_queue) eklenir - kaybolmaz,
    bağlantı gelince tekrar denenir. Chat id / retry-callback için
    TelegramMixin'e bağımlıdır.
    """

    REPORT_PERIOD_HOURS = 24
    REPORT_CHECK_INTERVAL_SECONDS = 300.0

    def _resolve_report_period_start(self, settings, now_utc):
        """
        Son rapor ne zaman gönderildiyse ondan bu yana geçen süreye
        bakar. REPORT_PERIOD_HOURS dolmadıysa None döner (henüz
        rapor zamanı değil). Hiç gönderilmemişse ya da tarih
        okunamıyorsa, son REPORT_PERIOD_HOURS'u kapsayan bir rapor
        için başlangıç noktası döner.
        """

        if not settings.last_daily_report_sent_at:
            return now_utc - timedelta(hours=self.REPORT_PERIOD_HOURS)

        try:
            last_sent = datetime.fromisoformat(
                settings.last_daily_report_sent_at
            )
        except Exception:
            return now_utc - timedelta(hours=self.REPORT_PERIOD_HOURS)

        elapsed_hours = (now_utc - last_sent).total_seconds() / 3600

        if elapsed_hours < self.REPORT_PERIOD_HOURS:
            return None

        return last_sent

    def _maybe_send_periodic_report(self):

        if not self._throttled(
            "_last_report_check_attempt",
            self.REPORT_CHECK_INTERVAL_SECONDS
        ):
            return

        if self.inspection_logger is None or self.current_band is None:
            return

        settings = self.telegram_settings_manager.load()

        if not settings.daily_report_enabled or not settings.is_configured():
            return

        now_utc = datetime.now(timezone.utc)

        since = self._resolve_report_period_start(settings, now_utc)

        if since is None:
            return

        if (
            self._telegram_report_thread is not None
            and self._telegram_report_thread.is_alive()
        ):
            return

        band = self.current_band
        logger_at_send_time = self.inspection_logger
        chat_ids = self._telegram_chat_ids(settings.chat_id)

        def _run():

            stats = logger_at_send_time.compute_period_stats(
                since.isoformat()
            )

            reports_folder = band.root / "telegram_reports"
            reports_folder.mkdir(parents=True, exist_ok=True)

            report_path = reports_folder / (
                f"rapor_{now_utc.strftime('%Y%m%d_%H%M%S')}.xlsx"
            )

            PeriodicReportExporter().export(
                stats, report_path, band.name, "Son 24 Saat Özeti"
            )

            caption = (
                f"📊 Günlük Özet - {band.name}\n"
                f"Toplam: {stats['total']} | UYGUN: {stats['ok_count']} | "
                f"HATA: {stats['ng_count']}"
            )

            for chat_id in chat_ids:

                notifier = TelegramNotifier(settings.bot_token, chat_id)

                message_id = notifier.send_document(
                    str(report_path), caption=caption
                )

                if message_id is None:

                    self.telegram_queue.enqueue(QueuedNotification(
                        kind="document",
                        bot_token=settings.bot_token,
                        chat_id=chat_id,
                        text=caption,
                        image_path=str(report_path)
                    ))

            updated_settings = self.telegram_settings_manager.load()
            updated_settings.last_daily_report_sent_at = (
                now_utc.isoformat()
            )
            self.telegram_settings_manager.save(updated_settings)

        self._telegram_report_thread = threading.Thread(
            target=_run, daemon=True
        )
        self._telegram_report_thread.start()
