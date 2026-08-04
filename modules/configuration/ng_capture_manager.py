from __future__ import annotations

import shutil
from datetime import datetime

import cv2

from .band import Band


class NGCaptureManager:

    FOLDER_NAME = "ng_captures"

    # -------------------------------------------------
    # NG Karesini Kaydet
    # -------------------------------------------------

    def save(self, band: Band, image) -> str | None:

        if image is None:
            return None

        folder = band.root / self.FOLDER_NAME
        folder.mkdir(parents=True, exist_ok=True)

        base_name = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        # Windows'ta saat çözünürlüğü mikrosaniyeden kaba olabilir;
        # art arda hızlı çağrılarda aynı damga üretilip önceki NG
        # fotoğrafının üzerine sessizce yazılmasını önlemek için
        # çakışma varsa sayaç ekle.
        path = folder / f"{base_name}.png"

        counter = 1

        while path.exists():

            path = folder / f"{base_name}_{counter}.png"
            counter += 1

        cv2.imwrite(str(path), image)

        return str(path)

    # -------------------------------------------------
    # Kaydedilen Fotoğrafları Temizle
    # -------------------------------------------------

    def clear(self, band: Band):

        folder = band.root / self.FOLDER_NAME

        shutil.rmtree(folder, ignore_errors=True)
