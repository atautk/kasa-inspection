from __future__ import annotations

import json
import zipfile
from pathlib import Path

from .band import Band
from .band_manager import BandManager


class BandExportManager:

    # -------------------------------------------------
    # Dışa Aktar
    # -------------------------------------------------

    def export_band(self, band: Band, destination_path: str):

        with zipfile.ZipFile(
            destination_path,
            "w",
            zipfile.ZIP_DEFLATED
        ) as zf:

            band_json_path = band.root / "band.json"

            if band_json_path.exists():
                zf.write(band_json_path, "band.json")

            if band.roi.exists():
                zf.write(band.roi, "roi.json")

            if band.reference.exists():
                zf.write(band.reference, "reference.png")

            if band.models.exists():

                for model_file in sorted(band.models.glob("*.json")):

                    zf.write(model_file, f"models/{model_file.name}")

    # -------------------------------------------------
    # İçe Aktar
    # -------------------------------------------------

    def import_band(
        self,
        band_manager: BandManager,
        source_path: str
    ) -> Band:

        with zipfile.ZipFile(source_path, "r") as zf:

            names = zf.namelist()

            if "band.json" not in names:

                raise ValueError(
                    "Geçersiz dosya: band.json bulunamadı."
                )

            with zf.open("band.json") as f:
                band_data = json.load(f)

            name = band_data.get("name", "İçe Aktarılan Band")
            camera = band_data.get("camera", 0)

            band = band_manager.create_band(name, camera=camera)

            band.threshold = band_data.get("threshold", 3.0)
            band.version = band_data.get("version", "1.0")

            band_manager.save_band(band)

            if "roi.json" in names:

                with zf.open("roi.json") as f:
                    band.roi.write_bytes(f.read())

            if "reference.png" in names:

                with zf.open("reference.png") as f:
                    band.reference.write_bytes(f.read())

            for entry in names:

                if entry.startswith("models/") and entry.endswith(".json"):

                    filename = Path(entry).name

                    with zf.open(entry) as f:
                        (band.models / filename).write_bytes(f.read())

        return band_manager.load_band(band.id)
