from dataclasses import dataclass, field
from pathlib import Path

from .camera_channel import CameraChannel


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

    # Aynı kasayı farklı açılardan izleyen EK kameralar. Birincil
    # kamera (camera/reference/roi alanları) burada YER ALMAZ - bu
    # sayede tek kameralı bandlar hiç değişmeden çalışmaya devam eder.
    cameras: list = field(default_factory=list)