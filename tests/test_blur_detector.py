import numpy as np

from modules.core.blur_detector import BlurDetector


def _sharp_image():
    """
    Yüksek kontrastlı bir dama tahtası deseni - keskin kenarlar
    (yüksek Laplacian varyansı, net).
    """

    image = np.zeros((200, 200, 3), dtype=np.uint8)

    image[::10, :] = 255
    image[:, ::10] = 255

    return image


def _blurry_image():
    """
    Düz, tek renkli bir görüntü - hiç kenar yok (Laplacian varyansı
    sıfıra yakın, tamamen bulanık/detaysız).
    """

    return np.full((200, 200, 3), 128, dtype=np.uint8)


def test_sharp_image_has_higher_sharpness_than_blurry_image():

    detector = BlurDetector()

    sharp_score = detector.compute_sharpness(_sharp_image())
    blurry_score = detector.compute_sharpness(_blurry_image())

    assert sharp_score > blurry_score


def test_flat_image_has_near_zero_sharpness():

    detector = BlurDetector()

    score = detector.compute_sharpness(_blurry_image())

    assert score < 1.0


def test_compute_sharpness_returns_plain_python_float():

    detector = BlurDetector()

    score = detector.compute_sharpness(_sharp_image())

    assert type(score) is float
