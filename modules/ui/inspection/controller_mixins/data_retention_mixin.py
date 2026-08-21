import threading
from datetime import datetime, timezone

from modules.utils.logger import get_logger

app_logger = get_logger()


class DataRetentionMixin:
    """
    Bandın veri saklama ayarı açıksa ve son kontrolün üzerinden
    DATA_RETENTION_CHECK_INTERVAL_HOURS'tan fazla süre geçtiyse, arka
    planda saklama süresini aşan kayıtları arşivleyip siler - bkz.
    DataRetentionManager.export_and_purge.
    """

    DATA_RETENTION_CHECK_INTERVAL_SECONDS = 3600.0
    DATA_RETENTION_CHECK_INTERVAL_HOURS = 24.0

    def _maybe_run_data_retention(self):

        if not self._throttled(
            "_last_data_retention_check_attempt",
            self.DATA_RETENTION_CHECK_INTERVAL_SECONDS
        ):
            return

        if self.current_band is None or self.inspection_logger is None:
            return

        if not self.current_band.data_retention_enabled:
            return

        destination = self.current_band.data_retention_export_destination

        if not destination:
            return

        now_utc = datetime.now(timezone.utc)

        if self.current_band.last_data_retention_run_at:

            try:

                last_run_at = datetime.fromisoformat(
                    self.current_band.last_data_retention_run_at
                )

                elapsed_hours = (
                    (now_utc - last_run_at).total_seconds() / 3600
                )

                if elapsed_hours < self.DATA_RETENTION_CHECK_INTERVAL_HOURS:
                    return

            except Exception:
                pass

        if (
            self._data_retention_thread is not None
            and self._data_retention_thread.is_alive()
        ):
            return

        band = self.current_band
        logger_at_run_time = self.inspection_logger

        def _run():

            try:

                self.data_retention_manager.export_and_purge(
                    band, logger_at_run_time, destination
                )

            except Exception as e:

                app_logger.warning(
                    "Veri saklama/arşivleme başarısız: %s -> %s (%s)",
                    band.name, destination, e
                )

                return

            updated_band = self.band_manager.load_band(band.id)
            updated_band.last_data_retention_run_at = now_utc.isoformat()
            self.band_manager.save_band(updated_band)

            if band is self.current_band:
                self.current_band.last_data_retention_run_at = (
                    now_utc.isoformat()
                )

            app_logger.info(
                "Veri saklama kontrolü tamamlandı: %s", band.name
            )

        self._data_retention_thread = threading.Thread(
            target=_run, daemon=True
        )
        self._data_retention_thread.start()
