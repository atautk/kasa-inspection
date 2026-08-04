import cv2
import numpy as np

from modules.core.inspection_engine import InspectionEngine


def _old_crop_polygon(image, points, margin=8):
    """
    Performans optimizasyonundan önceki (tüm görüntü boyutunda maske
    oluşturan) referans uygulama - yeni uygulamanın piksel bazında
    aynı sonucu ürettiğini doğrulamak için kullanılır.
    """

    polygon = np.array(points, dtype=np.int32)

    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    cv2.fillPoly(mask, [polygon], 255)

    masked = cv2.bitwise_and(image, image, mask=mask)

    x, y, w, h = cv2.boundingRect(polygon)

    x += margin
    y += margin
    w -= margin * 2
    h -= margin * 2

    x = max(0, x)
    y = max(0, y)
    w = min(w, image.shape[1] - x)
    h = min(h, image.shape[0] - y)

    if w <= 0 or h <= 0:
        return np.array([])

    return masked[y:y + h, x:x + w]


def _random_image(seed=0, size=(720, 1280, 3)):

    rng = np.random.default_rng(seed)

    return rng.integers(0, 255, size=size, dtype=np.uint8)


def test_crop_polygon_matches_full_frame_mask_approach_center():

    image = _random_image()

    points = [[300, 265], [559, 265], [554, 393], [303, 392]]

    old = _old_crop_polygon(image, points)
    new = InspectionEngine().crop_polygon(image, points)

    assert new.shape == old.shape
    assert np.array_equal(new, old)


def test_crop_polygon_matches_near_edge():

    image = _random_image()

    points = [[1200, 650], [1270, 650], [1270, 710], [1200, 710]]

    old = _old_crop_polygon(image, points)
    new = InspectionEngine().crop_polygon(image, points)

    assert new.shape == old.shape
    assert np.array_equal(new, old)


def test_crop_polygon_matches_top_left_corner():

    image = _random_image()

    points = [[0, 0], [50, 0], [50, 50], [0, 50]]

    old = _old_crop_polygon(image, points)
    new = InspectionEngine().crop_polygon(image, points)

    assert new.shape == old.shape
    assert np.array_equal(new, old)


def test_crop_polygon_none_image_returns_empty():

    result = InspectionEngine().crop_polygon(None, [[0, 0], [1, 0], [1, 1]])

    assert result.size == 0


def test_crop_polygon_too_small_after_margin_returns_empty():

    image = _random_image()

    # Marj (8px) sonrası kalan alan negatif/sıfır olacak kadar küçük
    points = [[10, 10], [14, 10], [14, 14], [10, 14]]

    result = InspectionEngine().crop_polygon(image, points)

    assert result.size == 0


def test_compare_reports_zero_change_for_identical_crops():

    image = _random_image()[:100, :100]

    compare = InspectionEngine().compare(image, image.copy())

    assert compare["change_ratio"] == 0
    assert compare["changed_pixels"] == 0


def test_compare_detects_change_when_crops_differ():

    base = np.zeros((100, 100, 3), dtype=np.uint8)
    changed = base.copy()
    changed[20:80, 20:80] = 255

    compare = InspectionEngine().compare(base, changed)

    assert compare["change_ratio"] > 0
    assert compare["changed_pixels"] > 0
