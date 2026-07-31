import numpy as np

from modules.core.reference_frame import ReferenceFrame


def make_image():

    return np.zeros((200, 200, 3), dtype=np.uint8)


def make_corners():

    return np.float32([
        [10, 10],
        [190, 10],
        [10, 190],
        [190, 190]
    ])


def test_generate_returns_warped_image_with_valid_corners():

    ref = ReferenceFrame(width=100, height=80)

    result = ref.generate(make_image(), make_corners())

    assert result is not None
    assert result.shape == (80, 100, 3)


def test_generate_returns_none_when_corners_missing():
    """
    Regresyon testi: kasa/markerlar tamamen kayboldu (frame_corners
    None) - eski, artık anlamsız hale gelmiş bir görüntüye geri
    dönmemeli, net bir şekilde "referans yok" (None) döndürmeli.
    """

    ref = ReferenceFrame(width=100, height=80)

    ref.generate(make_image(), make_corners())

    result = ref.generate(make_image(), None)

    assert result is None
    assert ref.last_frame is None


def test_generate_returns_none_when_corner_count_invalid():

    ref = ReferenceFrame(width=100, height=80)

    ref.generate(make_image(), make_corners())

    result = ref.generate(make_image(), make_corners()[:3])

    assert result is None
    assert ref.last_frame is None
