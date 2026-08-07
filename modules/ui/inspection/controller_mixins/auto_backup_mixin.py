import threading
from datetime import datetime, timezone

from modules.utils.logger import get_logger

app_logger = get_logger()


class AutoBackupMixin:
    """
    Bandın otomatik yedekleme ayarı açıksa ve son yedeklemenin
    üzerinden auto_backup_interval_hours'tan fazla süre geçtiyse,
    arka planda bir yedekleme başlatır (dosya kopyalama işlemi UI
    thread'ini bloklamasın diye). Eski yedekler otomatik temizlenir -
    bkz. BackupManager.backup_and_cleanup.
    """

    BACKUP_CHECK_INTERVAL_SECONDS = 3600.0

    def _maybe_run_auto_backup(self):

        if not self._throttled(
            "_last_backup_check_attempt", self.BACKUP_CHECK_INTERVAL_SECONDS
        ):
            return

        if self.current_band is None:
            return

        if not self.current_band.auto_backup_enabled:
            return

        destination = self.current_band.auto_backup_destination

        if not destination:
            return

        now_utc = datetime.now(timezone.utc)

        if self.current_band.last_auto_backup_at:

            try:

                last_backup_at = datetime.fromisoformat(
                    self.current_band.last_auto_backup_at
                )

                elapsed_hours = (
                    (now_utc - last_backup_at).total_seconds() / 3600
                )

                if elapsed_hours < self.current_band.auto_backup_interval_hours:
                    return

            except Exception:
                pass

        if (
            self._backup_thread is not None
            and self._backup_thread.is_alive()
        ):
            return

        band = self.current_band
        keep_count = band.auto_backup_keep_count

        def _run():

            try:

                self.backup_manager.backup_and_cleanup(
                    band, destination, keep_count
                )

            except Exception as e:

                app_logger.warning(
                    "Otomatik yedekleme başarısız: %s -> %s (%s)",
                    band.name, destination, e
                )

                return

            updated_band = self.band_manager.load_band(band.id)
            updated_band.last_auto_backup_at = now_utc.isoformat()
            self.band_manager.save_band(updated_band)

            if band is self.current_band:
                self.current_band.last_auto_backup_at = now_utc.isoformat()

            app_logger.info(
                "Otomatik yedekleme tamamlandı: %s -> %s",
                band.name, destination
            )

        self._backup_thread = threading.Thread(target=_run, daemon=True)
        self._backup_thread.start()
