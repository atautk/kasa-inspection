from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from .periodic_report_exporter import PeriodicReportExporter


class DataRetentionManager:
    """
    Bandın "en fazla N gün/ay/yıl" veri saklama ayarını uygular: bu
    süreden eski inceleme kayıtları silinmeden ÖNCE bir özet Excel
    raporu olarak dışa aktarılır (veri sessizce kaybolmasın diye),
    sonra InspectionLogger.delete_before ile DB'den ve ilişkili
    HATA/eğitim fotoğraflarından silinir.

    Gün/ay/yıl birimleri takvim hassasiyeti olmadan yaklaşık gün
    sayısına çevrilir (ay=30, yıl=365) - bir üretim/kalite kontrol
    saklama penceresi için bu yeterli hassasiyette.
    """

    PERIOD_UNIT_DAYS = {"day": 1, "month": 30, "year": 365}

    def resolve_max_days(self, period_value: int, period_unit: str) -> int:

        unit_days = self.PERIOD_UNIT_DAYS.get(period_unit, 365)

        return max(1, int(period_value)) * unit_days

    def export_and_purge(
        self, band, inspection_logger, destination_folder
    ) -> Path | None:
        """
        Saklama süresini aşan kayıt yoksa None döner ve hiçbir şey
        yapmaz. Varsa, arşiv Excel raporunun yolunu döner.
        """

        max_days = self.resolve_max_days(
            band.data_retention_period_value, band.data_retention_period_unit
        )

        cutoff = datetime.now(timezone.utc) - timedelta(days=max_days)
        cutoff_iso = cutoff.isoformat()

        stats = inspection_logger.compute_stats_before(cutoff_iso)

        if stats["total"] == 0:
            return None

        destination = Path(destination_folder)
        destination.mkdir(parents=True, exist_ok=True)

        report_path = destination / (
            f"{band.name}_veri_arsivi_{cutoff.strftime('%Y%m%d')}.xlsx"
        )

        PeriodicReportExporter().export(
            stats, report_path, band.name,
            f"{cutoff.date().isoformat()} Öncesi Arşiv Özeti"
        )

        image_paths = inspection_logger.delete_before(cutoff_iso)

        for path_str in image_paths:

            try:
                Path(path_str).unlink(missing_ok=True)
            except Exception:
                pass

        return report_path
