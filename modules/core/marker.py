from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class Marker:

    id: int

    corners: np.ndarray

    center: np.ndarray

    area: float

    rotation: float