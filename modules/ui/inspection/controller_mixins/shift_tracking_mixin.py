from datetime import datetime, timedelta, timezone


class ShiftTrackingMixin:
    """
    Vardiya bazlı üretim sayacı: bandın tanımlı vardiya pencereleri
    varsa (bkz. Band.shifts, ShiftSettingsDialog), şu an içinde
    bulunulan pencereyi bulur ve o pencerenin başlangıcından bu yana
    kaç kasa incelendiğini arayüzde gösterir. Üretim hedefi/tempo
    takibi ve buna bağlı Telegram uyarısı YOK - sadece bir sayaç.
    Şu an aktif bir vardiya penceresi içinde değilsek (veya hiç
    pencere tanımlı değilse) gösterge gizlenir.
    """

    SHIFT_CHECK_INTERVAL_SECONDS = 60.0

    def _maybe_check_shift_progress(self):

        if not self._throttled(
            "_last_shift_check_attempt", self.SHIFT_CHECK_INTERVAL_SECONDS
        ):
            return

        if self.current_band is None or self.inspection_logger is None:
            return

        active = self._active_shift_window(self.current_band.shifts)

        if active is None:
            self.page.set_shift_progress(None)
            return

        shift, window_start = active

        # InspectionLogger kayıtları UTC'de saklar ve compute_period_stats
        # "since" ile düz metin karşılaştırması yapar - pencere
        # başlangıcı da UTC'ye çevrilmeden gönderilirse (yerel saat
        # dilimi farkı nedeniyle) karşılaştırma yanlış sonuç verir.
        stats = self.inspection_logger.compute_period_stats(
            window_start.astimezone(timezone.utc).isoformat()
        )
        produced = stats["total"]

        self.page.set_shift_progress({
            "produced": produced,
            "name": shift.name,
            "start": shift.start,
            "end": shift.end,
            "operator": shift.operator
        })

    def _active_shift_window(self, shifts):
        """
        Şu an (yerel saatle) içinde bulunulan vardiya penceresini
        bulur - listedeki ilk eşleşen pencere kazanır (çakışan
        pencere tanımlanmışsa). Hiçbiri şu an aktif değilse None
        döner.
        """

        if not shifts:
            return None

        now_local = datetime.now().astimezone()

        for shift in shifts:

            window_start = self._shift_window_start_for(shift, now_local)

            if window_start is not None:
                return shift, window_start

        return None

    def _shift_window_start_for(self, shift, now_local):
        """
        `shift` (start/end "HH:MM") için, `now_local` bu pencerenin
        içindeyse pencerenin başlangıç zamanını döner - günü aşan
        (ör. 22:00-06:00 gece vardiyası) pencereler de desteklenir.
        `now_local` pencerenin dışındaysa None döner.
        """

        try:
            start_t = datetime.strptime(shift.start, "%H:%M").time()
            end_t = datetime.strptime(shift.end, "%H:%M").time()
        except ValueError:
            return None

        overnight = end_t <= start_t

        today_start = now_local.replace(
            hour=start_t.hour, minute=start_t.minute,
            second=0, microsecond=0
        )
        today_end = now_local.replace(
            hour=end_t.hour, minute=end_t.minute,
            second=0, microsecond=0
        )

        if overnight:
            today_end += timedelta(days=1)

        if today_start <= now_local < today_end:
            return today_start

        yesterday_start = today_start - timedelta(days=1)
        yesterday_end = today_end - timedelta(days=1)

        if yesterday_start <= now_local < yesterday_end:
            return yesterday_start

        return None
