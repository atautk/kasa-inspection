from __future__ import annotations

import json
import shutil
from pathlib import Path

from .band import Band
from modules.utils.logger import get_logger

app_logger = get_logger()


class BandManager:

    def __init__(self, root: Path | str = "configuration"):

        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------
    # Bantları Listele
    # -------------------------------------------------

    def list_bands(self) -> list[Band]:

        bands = []

        for folder in sorted(self.root.glob("band_*")):

            if not folder.is_dir():
                continue

            try:
                bands.append(self.load_band(folder.name))
            except Exception as e:

                # Bozuk/okunamayan band klasörü listeden sessizce
                # düşmesin - en azından log'a düşsün ki fark edilsin
                # (aksi halde bir band aniden kaybolmuş gibi görünür).
                app_logger.error(
                    "Band yüklenemedi, atlanıyor: %s (%s)",
                    folder.name,
                    e
                )

                continue

        return bands

    # -------------------------------------------------
    # Bant Oluştur
    # -------------------------------------------------

    def create_band(
        self,
        name: str,
        camera: int = 0
    ) -> Band:

        band_id = self._next_band_id()

        band_folder = self.root / band_id
        band_folder.mkdir()

        models_folder = band_folder / "models"
        models_folder.mkdir()

        roi_file = band_folder / "roi.json"

        with open(roi_file, "w", encoding="utf-8") as f:

            json.dump(
                {
                    "version": "1.0",
                    "rois": []
                },
                f,
                indent=4,
                ensure_ascii=False
            )

        band_json = {

            "id": band_id,
            "name": name,
            "camera": camera,
            "threshold": 3.0,
            "arduino_port": "",
            "version": "1.0"

        }

        with open(
            band_folder / "band.json",
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                band_json,
                f,
                indent=4,
                ensure_ascii=False
            )

        return self.load_band(band_id)

    # -------------------------------------------------
    # Bant Yükle
    # -------------------------------------------------

    def load_band(
        self,
        band_id: str
    ) -> Band:

        folder = self.root / band_id

        if not folder.exists():
            raise FileNotFoundError(band_id)

        with open(
            folder / "band.json",
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        return Band(

            id=data["id"],

            name=data["name"],

            root=folder,

            reference=folder / "reference.png",

            roi=folder / "roi.json",

            models=folder / "models",

            camera=data.get("camera", 0),

            threshold=data.get("threshold", 3.0),

            arduino_port=data.get("arduino_port", ""),

            version=data.get("version", "1.0")

        )

    # -------------------------------------------------
    # Bant Kaydet
    # -------------------------------------------------

    def save_band(
        self,
        band: Band
    ):

        band_json = {

            "id": band.id,
            "name": band.name,
            "camera": band.camera,
            "threshold": band.threshold,
            "arduino_port": band.arduino_port,
            "version": band.version

        }

        with open(
            band.root / "band.json",
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                band_json,
                f,
                indent=4,
                ensure_ascii=False
            )

    # -------------------------------------------------
    # Bant Sil
    # -------------------------------------------------

    def delete_band(
        self,
        band_id: str
    ):

        folder = self.root / band_id

        if folder.exists():

            shutil.rmtree(folder)

    # -------------------------------------------------
    # Bant Var mı?
    # -------------------------------------------------

    def exists(
        self,
        band_id: str
    ) -> bool:

        return (self.root / band_id).exists()

    # -------------------------------------------------
    # Sonraki Band ID
    # -------------------------------------------------

    def _next_band_id(self) -> str:

        numbers = []

        for folder in self.root.glob("band_*"):

            try:

                numbers.append(
                    int(folder.name.split("_")[1])
                )

            except Exception:
                pass

        next_number = 1

        if numbers:

            next_number = max(numbers) + 1

        return f"band_{next_number:02d}"