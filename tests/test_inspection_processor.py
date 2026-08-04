import numpy as np

from modules.core.inspection_processor import InspectionProcessor


class _FakeInspectionEngine:

    def crop_polygon(self, image, points):
        return np.ones((10, 10, 3), dtype=np.uint8)

    def compare(self, reference_crop, current_crop):
        return {
            "reference": reference_crop,
            "current": current_crop,
            "difference": None,
            "binary": None,
            "changed_pixels": 5,
            "change_ratio": 4.0
        }


class _FakeROIManager:

    def __init__(self, rois):
        self._rois = rois

    def get_rois(self):
        return self._rois


class _FakeRecipe:

    def __init__(self, expected=None, thresholds=None):
        self._expected = expected or {}
        self._thresholds = thresholds or {}

    def expected(self, roi_name):
        return self._expected.get(roi_name, "EMPTY")

    def threshold_for(self, roi_name):
        return self._thresholds.get(roi_name)


class _RecordingDecisionEngine:

    def __init__(self):
        self.calls = []

    def detect(self, result, threshold=None):
        self.calls.append(threshold)
        return "FULL" if threshold is not None and result["change_ratio"] >= threshold else "EMPTY"


def _rois(names):
    return [
        {"name": name, "points": [[0, 0], [10, 0], [10, 10], [0, 10]]}
        for name in names
    ]


def test_uses_model_specific_threshold_override_when_present():

    decision = _RecordingDecisionEngine()

    processor = InspectionProcessor(
        _FakeInspectionEngine(),
        _FakeROIManager(_rois(["G01"])),
        _FakeRecipe(thresholds={"G01": 2.0}),
        decision
    )

    result = processor.process(np.zeros((100, 100, 3), dtype=np.uint8), np.zeros((100, 100, 3), dtype=np.uint8))

    assert decision.calls == [2.0]
    assert result["results"]["G01"]["state"] == "FULL"


def test_falls_back_to_global_threshold_when_no_override():

    decision = _RecordingDecisionEngine()

    processor = InspectionProcessor(
        _FakeInspectionEngine(),
        _FakeROIManager(_rois(["G01"])),
        _FakeRecipe(thresholds={}),
        decision
    )

    processor.process(np.zeros((100, 100, 3), dtype=np.uint8), np.zeros((100, 100, 3), dtype=np.uint8))

    assert decision.calls == [None]


def test_different_rois_can_have_different_overrides():

    decision = _RecordingDecisionEngine()

    processor = InspectionProcessor(
        _FakeInspectionEngine(),
        _FakeROIManager(_rois(["G01", "G02"])),
        _FakeRecipe(thresholds={"G01": 1.0, "G02": 9.0}),
        decision
    )

    processor.process(np.zeros((100, 100, 3), dtype=np.uint8), np.zeros((100, 100, 3), dtype=np.uint8))

    assert set(decision.calls) == {1.0, 9.0}
