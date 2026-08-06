from unittest.mock import MagicMock

import numpy as np

from modules.core.aruco_detector import ArucoDetector


def _fake_detect_markers(ids):
    """
    cv2.aruco.ArucoDetector.detectMarkers()'ın döndürdüğü
    (corners, ids, rejected) biçimini taklit eder.
    """

    corners = [
        np.array(
            [[0, 0], [10, 0], [10, 10], [0, 10]], dtype=np.float32
        ).reshape(1, 4, 2)
        for _ in ids
    ]

    ids_array = (
        np.array(ids, dtype=np.int32).reshape(-1, 1) if ids else None
    )

    return corners, ids_array, None


def _detector_with_fake_backend(ids, extra_valid_markers=None):
    """
    cv2.aruco.ArucoDetector C++ nesnesi read-only olduğu için
    doğrudan patch edilemiyor - onun yerine ArucoDetector.detector
    özniteliğinin tamamını sahte bir nesneyle değiştiriyoruz.
    """

    detector = ArucoDetector(extra_valid_markers=extra_valid_markers)

    detector.detector = MagicMock()
    detector.detector.detectMarkers.return_value = _fake_detect_markers(ids)

    return detector


def test_default_valid_markers_matches_class_constant():

    detector = ArucoDetector()

    assert detector.valid_markers == {0, 1, 2, 3}


def test_extra_valid_markers_widens_set():

    detector = ArucoDetector(extra_valid_markers={4, 5})

    assert detector.valid_markers == {0, 1, 2, 3, 4, 5}


def test_no_extra_valid_markers_argument_behaves_like_before():

    detector = ArucoDetector(extra_valid_markers=None)

    assert detector.valid_markers == ArucoDetector.VALID_MARKERS


def test_detect_returns_empty_dict_when_no_markers_found():

    detector = _detector_with_fake_backend([])
    detector.detector.detectMarkers.return_value = (None, None, None)

    result = detector.detect(np.zeros((10, 10, 3), dtype=np.uint8))

    assert result == {}


def test_detect_filters_out_ids_not_in_default_valid_markers():

    detector = _detector_with_fake_backend([0, 4])

    result = detector.detect(np.zeros((10, 10, 3), dtype=np.uint8))

    assert set(result.keys()) == {0}


def test_detect_includes_widened_ids_when_configured():

    detector = _detector_with_fake_backend([0, 4], extra_valid_markers={4})

    result = detector.detect(np.zeros((10, 10, 3), dtype=np.uint8))

    assert set(result.keys()) == {0, 4}


def test_detect_still_ignores_ids_outside_widened_set():

    detector = _detector_with_fake_backend(
        [0, 4, 99], extra_valid_markers={4}
    )

    result = detector.detect(np.zeros((10, 10, 3), dtype=np.uint8))

    assert set(result.keys()) == {0, 4}


def test_detect_marker_fields_are_populated():

    detector = _detector_with_fake_backend([0])

    result = detector.detect(np.zeros((10, 10, 3), dtype=np.uint8))

    marker = result[0]

    assert marker.id == 0
    assert marker.corners.shape == (4, 2)
    assert marker.area > 0
