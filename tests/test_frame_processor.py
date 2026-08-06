from dataclasses import dataclass

import numpy as np

from modules.core.frame_processor import FrameProcessor


@dataclass
class _FakeMarker:

    id: int
    area: float = 100.0


class _FakeArucoDetector:

    def __init__(self, markers: dict):
        self.markers = markers
        self.received_frames = []

    def detect(self, frame):
        self.received_frames.append(frame)
        return self.markers


class _FakeLocalizer:

    def __init__(self):
        self.received_markers = None

    def update(self, markers):
        self.received_markers = markers
        return {
            "mode": "NORMAL",
            "visible": len(markers),
            "confidence": 100,
            "frame_corners": None,
            "settled": True
        }


class _FakeReferenceFrame:

    def generate(self, frame, corners):
        return "reference-image"


def _frame():
    return np.zeros((10, 10, 3), dtype=np.uint8)


def test_frame_is_none_returns_failure_with_identity_marker_none():

    processor = FrameProcessor(
        _FakeArucoDetector({}), _FakeLocalizer(), _FakeReferenceFrame()
    )

    result = processor.process(None)

    assert result["success"] is False
    assert result["identity_marker_id"] is None


def test_legacy_only_markers_0_to_3_are_unaffected():
    """
    1,2,3 dışında görülen tek aday '0'sa (eski/tek-marker'lı bant),
    yeniden eşleme tam bir no-op olmalı - localizer'a giden dict
    aynen aynı olmalı.
    """

    markers = {
        0: _FakeMarker(id=0), 1: _FakeMarker(id=1),
        2: _FakeMarker(id=2), 3: _FakeMarker(id=3)
    }

    localizer = _FakeLocalizer()
    processor = FrameProcessor(
        _FakeArucoDetector(markers), localizer, _FakeReferenceFrame()
    )

    result = processor.process(_frame())

    assert result["identity_marker_id"] == 0
    assert localizer.received_markers == markers
    assert result["markers"] == markers


def test_non_reserved_marker_is_remapped_to_slot_zero():
    """
    Sol-üstte marker 0 yerine marker 4 varsa (yeni bir model),
    localizer'a giden dict'te 4 nolu marker'ın YERİNE 0 anahtarı
    altında görünmesi gerekir - localization.py'nin hiç
    değiştirilmeden çalışabilmesi için.
    """

    marker_4 = _FakeMarker(id=4)

    markers = {
        4: marker_4, 1: _FakeMarker(id=1),
        2: _FakeMarker(id=2), 3: _FakeMarker(id=3)
    }

    localizer = _FakeLocalizer()
    processor = FrameProcessor(
        _FakeArucoDetector(markers), localizer, _FakeReferenceFrame()
    )

    result = processor.process(_frame())

    assert result["identity_marker_id"] == 4

    # localizer'a giden (eşlenmiş) dict'te anahtar 0
    assert 0 in localizer.received_markers
    assert localizer.received_markers[0] is marker_4
    assert 4 not in localizer.received_markers

    # ham markers dict'i (dışarı döndürülen) DEĞİŞMEDEN kalmalı
    assert result["markers"] == markers
    assert 4 in result["markers"]


def test_no_identity_marker_candidate_leaves_markers_unmapped():
    """
    Sadece 1,2,3 görünüyorsa (sol-üst marker hiç görünmüyor),
    identity_marker_id None olmalı ve mevcut RECOVERY/ESTIMATE
    davranışı hiç etkilenmemeli.
    """

    markers = {1: _FakeMarker(id=1), 2: _FakeMarker(id=2)}

    localizer = _FakeLocalizer()
    processor = FrameProcessor(
        _FakeArucoDetector(markers), localizer, _FakeReferenceFrame()
    )

    result = processor.process(_frame())

    assert result["identity_marker_id"] is None
    assert localizer.received_markers == markers


def test_multiple_candidates_picks_largest_area():

    small = _FakeMarker(id=4, area=50.0)
    large = _FakeMarker(id=7, area=999.0)

    markers = {4: small, 7: large, 1: _FakeMarker(id=1)}

    processor = FrameProcessor(
        _FakeArucoDetector(markers), _FakeLocalizer(), _FakeReferenceFrame()
    )

    result = processor.process(_frame())

    assert result["identity_marker_id"] == 7


def test_reference_generated_only_when_frame_corners_present():

    class _LocalizerWithCorners(_FakeLocalizer):

        def update(self, markers):
            data = super().update(markers)
            data["frame_corners"] = np.zeros((4, 2))
            return data

    processor = FrameProcessor(
        _FakeArucoDetector({}), _LocalizerWithCorners(), _FakeReferenceFrame()
    )

    result = processor.process(_frame())

    assert result["reference"] == "reference-image"


def test_exception_in_pipeline_returns_failure_with_identity_marker_none():

    class _BrokenAruco:
        def detect(self, frame):
            raise RuntimeError("boom")

    processor = FrameProcessor(
        _BrokenAruco(), _FakeLocalizer(), _FakeReferenceFrame()
    )

    result = processor.process(_frame())

    assert result["success"] is False
    assert result["identity_marker_id"] is None
