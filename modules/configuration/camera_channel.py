from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class CameraChannel:
    """
    Bir kasayı farklı bir açıdan izleyen EK kamera. Her kanalın kendi
    fiziksel kamera indeksi, kendi referans fotoğrafı ve kendi ROI
    seti vardır.

    Band'ın "birincil" kamerası (band.camera/reference/roi) bu
    listede YER ALMAZ - geriye dönük uyumluluk için ayrı alanlar
    olarak kalır. cameras listesi sadece EK kanalları tutar.
    """

    id: str
    name: str
    camera_index: int

    reference: Path
    roi: Path
