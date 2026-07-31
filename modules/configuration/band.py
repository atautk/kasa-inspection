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