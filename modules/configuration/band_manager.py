from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from .band import Band
from .camera_channel import CameraChannel
from .shift_window import ShiftWindow
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
            "version": "1.0",
            "confirm_frames": 3

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

        cameras = [
            CameraChannel(
                id=entry["id"],
                name=entry["name"],
                camera_index=entry.get("camera_index", 0),
                reference=folder / entry["reference"],
                roi=folder / entry["roi"]
            )
            for entry in data.get("cameras", [])
        ]

        shifts = [
            ShiftWindow(
                id=entry["id"],
                name=entry["name"],
                start=entry["start"],
                end=entry["end"],
                operator=entry.get("operator", "")
            )
            for entry in data.get("shifts", [])
        ]

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

            version=data.get("version", "1.0"),

            confirm_frames=data.get("confirm_frames", 3),

            cameras=cameras,

            shifts=shifts,

            blur_threshold=data.get("blur_threshold", 100.0),

            reference_max_age_days=data.get("reference_max_age_days", 0),

            training_data_collection_enabled=data.get(
                "training_data_collection_enabled", False
            ),

            auto_backup_enabled=data.get("auto_backup_enabled", False),

            auto_backup_destination=data.get(
                "auto_backup_destination", ""
            ),

            auto_backup_interval_hours=data.get(
                "auto_backup_interval_hours", 24.0
            ),

            auto_backup_keep_count=data.get("auto_backup_keep_count", 30),

            last_auto_backup_at=data.get("last_auto_backup_at", "")

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
            "version": band.version,
            "confirm_frames": band.confirm_frames,

            "cameras": [
                {
                    "id": channel.id,
                    "name": channel.name,
                    "camera_index": channel.camera_index,
                    "reference": str(
                        channel.reference.relative_to(band.root)
                    ).replace("\\", "/"),
                    "roi": str(
                        channel.roi.relative_to(band.root)
                    ).replace("\\", "/")
                }
                for channel in band.cameras
            ],

            "shifts": [
                {
                    "id": shift.id,
                    "name": shift.name,
                    "start": shift.start,
                    "end": shift.end,
                    "operator": shift.operator
                }
                for shift in band.shifts
            ],

            "blur_threshold": band.blur_threshold,
            "reference_max_age_days": band.reference_max_age_days,
            "training_data_collection_enabled": (
                band.training_data_collection_enabled
            ),
            "auto_backup_enabled": band.auto_backup_enabled,
            "auto_backup_destination": band.auto_backup_destination,
            "auto_backup_interval_hours": band.auto_backup_interval_hours,
            "auto_backup_keep_count": band.auto_backup_keep_count,
            "last_auto_backup_at": band.last_auto_backup_at

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
    # Ek Kamera Kanalları (aynı kasayı farklı açıdan izleyen kameralar)
    # -------------------------------------------------

    def add_camera_channel(
        self,
        band: Band,
        name: str,
        camera_index: int
    ) -> CameraChannel:

        channel_id = uuid.uuid4().hex[:8]

        channel_folder = band.root / "cameras" / channel_id
        channel_folder.mkdir(parents=True, exist_ok=True)

        roi_file = channel_folder / "roi.json"

        with open(roi_file, "w", encoding="utf-8") as f:

            json.dump(
                {"version": "1.0", "rois": []},
                f,
                indent=4,
                ensure_ascii=False
            )

        channel = CameraChannel(
            id=channel_id,
            name=name,
            camera_index=camera_index,
            reference=channel_folder / "reference.png",
            roi=roi_file
        )

        band.cameras.append(channel)

        self.save_band(band)

        return channel

    def remove_camera_channel(self, band: Band, channel_id: str):

        band.cameras = [
            channel for channel in band.cameras
            if channel.id != channel_id
        ]

        self.save_band(band)

    # -------------------------------------------------
    # Vardiya Pencereleri (sabit saat aralıkları)
    # -------------------------------------------------

    def add_shift(
        self,
        band: Band,
        name: str,
        start: str,
        end: str,
        operator: str = ""
    ) -> ShiftWindow:

        shift = ShiftWindow(
            id=uuid.uuid4().hex[:8],
            name=name,
            start=start,
            end=end,
            operator=operator
        )

        band.shifts.append(shift)

        self.save_band(band)

        return shift

    def update_shift(
        self,
        band: Band,
        shift_id: str,
        name: str,
        start: str,
        end: str,
        operator: str = ""
    ):

        for shift in band.shifts:

            if shift.id == shift_id:
                shift.name = name
                shift.start = start
                shift.end = end
                shift.operator = operator
                break

        self.save_band(band)

    def remove_shift(self, band: Band, shift_id: str):

        band.shifts = [
            shift for shift in band.shifts
            if shift.id != shift_id
        ]

        self.save_band(band)

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