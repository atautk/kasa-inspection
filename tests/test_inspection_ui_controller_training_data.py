from pathlib import Path

import numpy as np
import pytest

from modules.configuration.band import Band


@pytest.fixture(scope="module")
def qapp():

    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


@pytest.fixture
def controller(qapp, tmp_path):

    from modules.ui.inspection.inspection_window import InspectionWindow
    from modules.ui.inspection.inspection_ui_controller import (
        InspectionUIController
    )

    window = InspectionWindow()

    ctrl = InspectionUIController(window, root=tmp_path, operator_name="test")

    band = Band(
        id="band_01",
        name="Test Bandı",
        root=tmp_path / "band_01",
        reference=tmp_path / "band_01" / "reference.png",
        roi=tmp_path / "band_01" / "roi.json",
        models=tmp_path / "band_01" / "models"
    )
    band.root.mkdir(parents=True, exist_ok=True)

    ctrl.current_band = band

    yield ctrl

    window.close()


def _crop():

    return np.zeros((20, 20, 3), dtype=np.uint8)


def _combined_results(**overrides):

    results = {
        "G01": {"state": "FULL", "expected": "FULL", "ok": True,
                 "change_ratio": 1.0}
    }
    results.update(overrides)
    return results


def _debug_entry():

    return {"reference": _crop(), "current": _crop()}


def test_returns_empty_dict_when_debug_is_none(controller):

    result = controller._save_training_images(_combined_results(), None)

    assert result == {}


def test_returns_empty_dict_when_debug_is_empty(controller):

    result = controller._save_training_images(_combined_results(), {})

    assert result == {}


def test_saves_crop_pair_for_each_roi_in_debug(controller):

    debug = {"G01": _debug_entry()}

    result = controller._save_training_images(_combined_results(), debug)

    assert "G01" in result
    assert Path(result["G01"]["reference"]).exists()
    assert Path(result["G01"]["current"]).exists()


def test_uses_roi_state_as_label_folder(controller):

    debug = {"G01": _debug_entry()}
    combined = _combined_results()
    combined["G01"]["state"] = "EMPTY"

    result = controller._save_training_images(combined, debug)

    saved_path = Path(result["G01"]["current"])
    assert saved_path.parent.name == "EMPTY"
    assert saved_path.parent.parent.name == "G01"


def test_skips_roi_present_in_debug_but_missing_from_combined_results(
    controller
):

    debug = {"G01": _debug_entry(), "G02": _debug_entry()}
    combined = _combined_results()  # sadece G01 var

    result = controller._save_training_images(combined, debug)

    assert "G01" in result
    assert "G02" not in result


def test_multiple_rois_each_get_their_own_folder(controller):

    debug = {"G01": _debug_entry(), "G02": _debug_entry()}
    combined = _combined_results(
        G02={"state": "EMPTY", "expected": "EMPTY", "ok": True,
             "change_ratio": 0.0}
    )

    result = controller._save_training_images(combined, debug)

    assert set(result.keys()) == {"G01", "G02"}
    assert (
        Path(result["G01"]["current"]).parent
        != Path(result["G02"]["current"]).parent
    )
