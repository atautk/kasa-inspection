from unittest.mock import MagicMock

import numpy as np
import pytest

from modules.configuration.camera_channel import CameraChannel


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

    return InspectionUIController(window, root=tmp_path, operator_name="test")


def _channel(tmp_path, name="Yan"):

    return CameraChannel(
        id="ch1",
        name=name,
        camera_index=1,
        reference=tmp_path / "reference.png",
        roi=tmp_path / "roi.json"
    )


def _channel_state(tmp_path, results, success=True, ret=True, name="Yan"):

    fake_cap = MagicMock()
    fake_cap.read.return_value = (
        ret, np.zeros((100, 100, 3), dtype=np.uint8)
    )

    fake_inspection_controller = MagicMock()
    fake_inspection_controller.process.return_value = {
        "success": success,
        "results": results,
        "reference_display": np.zeros((80, 80, 3), dtype=np.uint8)
    }

    return {
        "channel": _channel(tmp_path, name=name),
        "cap": fake_cap,
        "inspection_controller": fake_inspection_controller,
        "reference_image": None,
        "roi_manager": None
    }


def _primary_results():

    return {
        "G01": {
            "ok": True,
            "state": "FULL",
            "expected": "FULL",
            "change_ratio": 1.0,
            "changed_pixels": 1
        }
    }


def test_no_extra_channels_returns_primary_results_unchanged(controller):

    primary_results = _primary_results()
    primary_display = np.zeros((100, 100, 3), dtype=np.uint8)

    combined_results, combined_display = (
        controller._build_combined_results_and_display(
            primary_results, primary_display
        )
    )

    assert combined_results == primary_results
    assert combined_display is primary_display


def test_extra_channel_roi_names_are_qualified_with_channel_name(
    controller, tmp_path
):

    controller.extra_channels = {
        "ch1": _channel_state(
            tmp_path,
            results={"G01": {"ok": False, "state": "EMPTY",
                              "expected": "FULL", "change_ratio": 0.5,
                              "changed_pixels": 2}},
            name="Yan"
        )
    }

    combined_results, _ = controller._build_combined_results_and_display(
        _primary_results(), np.zeros((100, 100, 3), dtype=np.uint8)
    )

    # birincil kanalın nitelenmemiş G01'i ile ek kanalın "Yan:G01"i
    # birbirine karışmamalı
    assert "G01" in combined_results
    assert combined_results["G01"]["ok"] is True

    assert "Yan:G01" in combined_results
    assert combined_results["Yan:G01"]["ok"] is False


def test_two_extra_channels_with_same_roi_name_do_not_collide(
    controller, tmp_path
):

    controller.extra_channels = {
        "ch1": _channel_state(
            tmp_path,
            results={"G01": {"ok": True, "state": "FULL",
                              "expected": "FULL", "change_ratio": 1.0,
                              "changed_pixels": 1}},
            name="Yan"
        ),
        "ch2": _channel_state(
            tmp_path,
            results={"G01": {"ok": False, "state": "EMPTY",
                              "expected": "FULL", "change_ratio": 0.5,
                              "changed_pixels": 2}},
            name="Üst"
        )
    }

    combined_results, _ = controller._build_combined_results_and_display(
        _primary_results(), np.zeros((100, 100, 3), dtype=np.uint8)
    )

    assert combined_results["Yan:G01"]["ok"] is True
    assert combined_results["Üst:G01"]["ok"] is False


def test_channel_with_no_open_camera_is_skipped(controller, tmp_path):

    state = _channel_state(tmp_path, results={"G01": {"ok": False}})
    state["cap"] = None

    controller.extra_channels = {"ch1": state}

    combined_results, combined_display = (
        controller._build_combined_results_and_display(
            _primary_results(), np.zeros((100, 100, 3), dtype=np.uint8)
        )
    )

    assert combined_results == _primary_results()


def test_channel_with_failed_frame_read_is_skipped(controller, tmp_path):

    state = _channel_state(
        tmp_path, results={"G01": {"ok": False}}, ret=False
    )

    controller.extra_channels = {"ch1": state}

    combined_results, _ = controller._build_combined_results_and_display(
        _primary_results(), np.zeros((100, 100, 3), dtype=np.uint8)
    )

    assert combined_results == _primary_results()


def test_channel_with_unsuccessful_processing_is_skipped(
    controller, tmp_path
):

    state = _channel_state(
        tmp_path, results={"G01": {"ok": False}}, success=False
    )

    controller.extra_channels = {"ch1": state}

    combined_results, _ = controller._build_combined_results_and_display(
        _primary_results(), np.zeros((100, 100, 3), dtype=np.uint8)
    )

    assert combined_results == _primary_results()


def test_combined_display_is_wider_after_hconcat(controller, tmp_path):

    controller.extra_channels = {
        "ch1": _channel_state(tmp_path, results={})
    }

    primary_display = np.zeros((100, 100, 3), dtype=np.uint8)

    _, combined_display = controller._build_combined_results_and_display(
        _primary_results(), primary_display
    )

    assert combined_display.shape[1] > primary_display.shape[1]


def test_hconcat_images_resizes_to_matching_height(controller):

    left = np.zeros((100, 200, 3), dtype=np.uint8)
    right = np.zeros((50, 100, 3), dtype=np.uint8)

    combined = controller._hconcat_images(left, right)

    assert combined.shape[0] == 50
    assert combined.shape[1] == 200
