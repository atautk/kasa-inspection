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
