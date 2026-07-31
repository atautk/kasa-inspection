import numpy as np

from modules.core.marker import Marker
from modules.core.localization import LocalizationEngine


def make_marker(marker_id):

    corners = np.array([
        [marker_id * 10, 0],
        [marker_id * 10 + 1, 0],
        [marker_id * 10 + 1, 1],
        [marker_id * 10, 1]
    ], dtype=np.float32)

    return Marker(
        id=marker_id,
        corners=corners,
        center=corners.mean(axis=0),
        area=1.0,
        rotation=0.0
    )


def make_markers(ids):

    return {i: make_marker(i) for i in ids}


def test_all_four_markers_gives_normal_mode_and_full_confidence():

    engine = LocalizationEngine()

    result = engine.update(make_markers([0, 1, 2, 3]))

    assert result["mode"] == "NORMAL"
    assert result["visible"] == 4
    assert result["confidence"] == 100
    assert result["frame_corners"] is not None
    assert result["frame_corners"].shape == (4, 2)


def test_three_markers_with_prior_frame_gives_recovery():

    engine = LocalizationEngine()
    engine.update(make_markers([0, 1, 2, 3]))

    result = engine.update(make_markers([0, 1, 2]))

    assert result["mode"] == "RECOVERY"
    assert result["visible"] == 3
    assert result["confidence"] == 90
    assert result["frame_corners"] is not None


def test_two_markers_gives_estimate_mode():

    engine = LocalizationEngine()

    result = engine.update(make_markers([0, 1]))

    assert result["mode"] == "ESTIMATE"
    assert result["confidence"] == 70


def test_no_markers_gives_fail_mode_and_zero_confidence():

    engine = LocalizationEngine()

    result = engine.update({})

    assert result["mode"] == "FAIL"
    assert result["visible"] == 0
    assert result["confidence"] == 0
    assert result["frame_corners"] is None


def test_recovery_uses_correct_marker_corner_index():
    """
    Regresyon testi: ArucoDetector, markers sözlüğüne dict yerine
    Marker nesnesi koyuyor. LocalizationEngine bunlara marker.corners
    (attribute) ile erişmeli, marker["corners"] (dict-style) ile değil.
    """

    engine = LocalizationEngine()

    result = engine.update(make_markers([0, 1, 2, 3]))

    expected = np.float32([
        make_marker(0).corners[0],
        make_marker(1).corners[1],
        make_marker(2).corners[3],
        make_marker(3).corners[2]
    ])

    np.testing.assert_array_equal(result["frame_corners"], expected)


def test_total_marker_loss_does_not_reuse_stale_frame():
    """
    Regresyon testi: kasa/markerlar (0 veya 1 görünür - FAIL) tamamen
    kaybolduğunda son bilinen kareyi kullanmaya devam etmemeli.
    Aksi halde kasa tamamen çekilse bile inspection eski, artık
    anlamsız bir kareyle OK/NG üretmeye devam eder.
    """

    engine = LocalizationEngine()
    engine.update(make_markers([0, 1, 2, 3]))

    result = engine.update({})

    assert result["mode"] == "FAIL"
    assert result["frame_corners"] is None
    assert engine.last_frame_corners is None


def test_single_marker_also_counts_as_total_loss():

    engine = LocalizationEngine()
    engine.update(make_markers([0, 1, 2, 3]))

    result = engine.update(make_markers([0]))

    assert result["mode"] == "FAIL"
    assert result["frame_corners"] is None


def test_reacquiring_after_total_loss_does_not_use_pre_loss_geometry():
    """
    Kasa tamamen kaybolduktan sonra (FAIL) geri geldiğinde, henüz
    tam (4 marker) bir kilit sağlanmadan RECOVERY/ESTIMATE modunun
    eski (kaybolmadan önceki) konumu kullanmaması gerekir - aksi
    halde farklı biçimde yerleştirilmiş yeni bir kasa, eski kasanın
    konumuyla karışabilir.
    """

    engine = LocalizationEngine()
    engine.update(make_markers([0, 1, 2, 3]))

    engine.update({})  # kasa tamamen kayboldu (FAIL)

    result = engine.update(make_markers([0, 1, 2]))  # 3 marker geri geldi

    assert result["mode"] == "RECOVERY"
    assert result["frame_corners"] is None
