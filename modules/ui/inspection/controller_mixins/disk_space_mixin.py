from modules.utils.logger import get_logger
from modules.utils.disk_monitor import get_free_space_gb

app_logger = get_logger()


class DiskSpaceMixin:
    """
    Band klasörünün bulunduğu diskte boş alan azalıyorsa arayüzde
    uyarır.
    """

    DISK_WARNING_THRESHOLD_GB = 5.0
    DISK_CHECK_INTERVAL_SECONDS = 60.0

    def _check_disk_space(self):

        if not self._throttled(
            "last_disk_check", self.DISK_CHECK_INTERVAL_SECONDS
        ):
            return

        check_path = (
            self.current_band.root
            if self.current_band is not None
            else self.band_manager.root
        )

        free_gb = get_free_space_gb(check_path)

        if free_gb < self.DISK_WARNING_THRESHOLD_GB:

            self.page.show_disk_warning(free_gb)

            if not self.disk_warning_active:

                app_logger.warning(
                    "Disk alanı azalıyor: %.1f GB kaldı (band=%s)",
                    free_gb,
                    self.current_band.name if self.current_band is not None else "?"
                )

                self.disk_warning_active = True

        else:

            self.page.hide_disk_warning()
            self.disk_warning_active = False
