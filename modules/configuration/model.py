from dataclasses import dataclass


@dataclass(slots=True)
class Model:

    id: str
    name: str

    expected_rois: list[str]

    version: str = "1.0"