from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Band:
    id: str
    name: str
    root: Path

    reference: Path
    roi: Path
    models: Path

    camera: int = 0
    threshold: float = 3.0
    arduino_port: str = ""
    version: str = "1.0"

    # Kamera titremesi/geçici gürültü nedeniyle OK<->NG durumu tek bir
    # karede yanlışlıkla değişebilir. Bir değişikliğin loglanıp
    # bildirilmesi için bu kadar ardışık karede tutarlı kalması
    # gerekir - bkz. InspectionLogger.
    confirm_frames: int = 3