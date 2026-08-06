from __future__ import annotations

import json
import shutil
from datetime import datetime

import cv2

from .band import Band


class UnknownKasaCaptureManager:
    """
    Sol-üst marker ID'si hiçbir modele eşleşmeyen (tanınmayan) bir
    kasa görüldüğünde, OK/NG kararı vermek yerine fotoğrafı ve o
    anki ROI'lerin ham dolu/boş durumunu diske kaydeder - mühendis
    daha sonra bu gerçek veriye bakıp yeni modeli tanımlayabilir.
    """

    FOLDER_NAME = "unknown_kasa_captures"

    # -------------------------------------------------
    # Tanınmayan Kasayı Kaydet
    # -------------------------------------------------

    def save(
        self,
        band: Band,
        image,
        marker_id: int,
        roi_states: dict
    ) -> str | None:

        if image is None:
            return None

        folder = band.root / self.FOLDER_NAME
        folder.mkdir(parents=True, exist_ok=True)

        base_name = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        path = folder / f"{base_name}_marker{marker_id}.png"

        counter = 1

        while path.exists():

            path = folder / f"{base_name}_marker{marker_id}_{counter}.png"
            counter += 1

        cv2.imwrite(str(path), image)

        metadata = {
            "marker_id": marker_id,
            "timestamp": datetime.now().isoformat(),
            "roi_states": roi_states
        }

        path.with_suffix(".json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        return str(path)

    # -------------------------------------------------
    # Kaydedilen Fotoğrafları Temizle
    # -------------------------------------------------

    def clear(self, band: Band):

        folder = band.root / self.FOLDER_NAME

        shutil.rmtree(folder, ignore_errors=True)
