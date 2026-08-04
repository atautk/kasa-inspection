from pathlib import Path

import cv2
import numpy as np

from modules.core.roi_auto_detector import ROIAutoDetector

FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "configuration" / "band_01" / "reference.png"
)


def test_detects_five_cells_in_reading_order():

    image = cv2.imread(str(FIXTURE))

    rois = ROIAutoDetector().detect(image)

    assert len(rois) == 5

    centroids = []

    for points in rois:
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        centroids.append((sum(xs) / 4, sum(ys) / 4))

    # Beklenen düzen: 2 satır x 2 sütun + tek başına bir alt hücre.
    # Satırlar y'ye göre artan, her satırda x'e göre artan olmalı.
    xs_top = [centroids[0][0], centroids[1][0]]
    assert xs_top[0] < xs_top[1]

    assert centroids[0][1] < centroids[2][1] < centroids[4][1]


def test_empty_image_returns_no_rois():

    blank = np.full((400, 400, 3), 255, dtype=np.uint8)

    rois = ROIAutoDetector().detect(blank)

    assert rois == []


def test_none_image_returns_empty_list():

    assert ROIAutoDetector().detect(None) == []
