from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from .band import Band


class BackupManager:
    """
    Bir bandın inspection geçmişini (SQLite log + NG fotoğrafları)
    seçilen bir hedef klasöre kopyalar. Orijinaller silinmez —
    bu bir yedekleme, temizlik değil.
    """

    def backup_band(self, band: Band, destination_folder) -> Path:

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        target = Path(destination_folder) / f"{band.name}_yedek_{timestamp}"

        target.mkdir(parents=True, exist_ok=True)

        db_path = band.root / "inspection_log.db"

        if db_path.exists():
            shutil.copy2(db_path, target / "inspection_log.db")

        ng_captures = band.root / "ng_captures"

        if ng_captures.exists() and any(ng_captures.iterdir()):
            shutil.copytree(
                ng_captures,
                target / "ng_captures",
                dirs_exist_ok=True
            )

        return target

    # -------------------------------------------------
    # Eski Yedekleri Temizle (Otomatik Yedekleme İçin)
    # -------------------------------------------------

    def cleanup_old_backups(
        self,
        band: Band,
        destination_folder,
        keep_count: int
    ):
        """
        destination_folder altında bu banda ait yedek klasörlerini
        (isim deseni: "<band.name>_yedek_<zaman damgası>") bulur, en
        yeni keep_count tanesini tutup gerisini siler. Zaman damgası
        formatı (YYYYMMDD_HHMMSS) isim sırasına göre sıralandığında
        zaten kronolojik sıra veriyor. keep_count <= 0 ise hiçbir
        şey silmez (otomatik temizlik kapalı sayılır).
        """

        if keep_count <= 0:
            return

        destination = Path(destination_folder)

        if not destination.exists():
            return

        prefix = f"{band.name}_yedek_"

        backups = sorted(
            (
                item for item in destination.iterdir()
                if item.is_dir() and item.name.startswith(prefix)
            ),
            key=lambda item: item.name
        )

        for old_backup in backups[:-keep_count]:
            shutil.rmtree(old_backup, ignore_errors=True)

    # -------------------------------------------------

    def backup_and_cleanup(
        self,
        band: Band,
        destination_folder,
        keep_count: int
    ) -> Path:

        target = self.backup_band(band, destination_folder)

        self.cleanup_old_backups(band, destination_folder, keep_count)

        return target
