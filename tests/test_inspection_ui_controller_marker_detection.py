import json
from pathlib import Path

import numpy as np
import pytest

from modules.configuration.band import Band
from modules.configuration.model import Model
from modules.configuration.telegram_settings import TelegramSettings
from modules.core.telegram_notifier import TelegramNotifier


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
    band.models.mkdir(parents=True, exist_ok=True)

    ctrl.current_band = band

    yield ctrl

    window.close()


def _model(model_id, name, marker_id):

    return Model(
        id=model_id, name=name, expected_rois=[], marker_id=marker_id
    )


def _result(identity_marker_id, results=None, reference_display=None):

    if reference_display is None:
        reference_display = np.zeros((10, 10, 3), dtype=np.uint8)

    return {
        "identity_marker_id": identity_marker_id,
        "results": results or {},
        "reference": None,
        "reference_display": reference_display
    }


def _setup_two_models(controller, current_index=0):

    model_a = _model("a", "Model A", marker_id=0)
    model_b = _model("b", "Model B", marker_id=4)

    controller.models = [model_a, model_b]
    controller.current_model = controller.models[current_index]
    controller.page.set_model_list(["Model A", "Model B"])
    controller.page.model_combo.setCurrentIndex(current_index)

    controller._rebuild_marker_id_map()

    return model_a, model_b


# -------------------------------------------------
# _rebuild_marker_id_map
# -------------------------------------------------

def test_no_models_with_marker_id_disables_detection(controller):

    controller.models = [_model("a", "Model A", marker_id=None)]
    controller.current_model = controller.models[0]

    controller._rebuild_marker_id_map()

    assert controller._marker_detection_enabled is False
    assert controller._marker_id_to_model == {}


def test_models_with_marker_id_enable_detection(controller):

    _setup_two_models(controller)

    assert controller._marker_detection_enabled is True
    assert set(controller._marker_id_to_model.keys()) == {0, 4}


# -------------------------------------------------
# Debounce
# -------------------------------------------------

def test_switch_does_not_happen_below_confirm_threshold(controller):

    _setup_two_models(controller, current_index=0)

    for _ in range(controller.MARKER_SWITCH_CONFIRM_FRAMES - 1):
        controller._handle_marker_model_detection(_result(4))

    assert controller.current_model.marker_id == 0


def test_switch_happens_at_confirm_threshold(controller):

    _setup_two_models(controller, current_index=0)

    for _ in range(controller.MARKER_SWITCH_CONFIRM_FRAMES):
        controller._handle_marker_model_detection(_result(4))

    assert controller.current_model.marker_id == 4
    assert controller.current_model.name == "Model B"


def test_flicker_between_candidates_resets_streak(controller):

    _setup_two_models(controller, current_index=0)

    # Kararsız okuma: 4, 0, 4, 0... asla aynı ID ardışık
    # MARKER_SWITCH_CONFIRM_FRAMES kere görülmüyor.
    for _ in range(20):
        controller._handle_marker_model_detection(_result(4))
        controller._handle_marker_model_detection(_result(0))

    assert controller.current_model.marker_id == 0


def test_same_marker_as_current_model_is_a_no_op(controller):

    _setup_two_models(controller, current_index=0)

    for _ in range(controller.MARKER_SWITCH_CONFIRM_FRAMES):
        is_unknown = controller._handle_marker_model_detection(_result(0))

    assert is_unknown is False
    assert controller.current_model.marker_id == 0


def test_switch_updates_model_combo_selection(controller):

    _setup_two_models(controller, current_index=0)

    for _ in range(controller.MARKER_SWITCH_CONFIRM_FRAMES):
        controller._handle_marker_model_detection(_result(4))

    assert controller.page.model_combo.currentIndex() == 1


def test_switch_rebuilds_recipe_manager(controller):

    _setup_two_models(controller, current_index=0)

    original_recipe_manager = controller.recipe_manager

    for _ in range(controller.MARKER_SWITCH_CONFIRM_FRAMES):
        controller._handle_marker_model_detection(_result(4))

    assert controller.recipe_manager is not original_recipe_manager
    assert controller.recipe_manager.model.id == "b"


# -------------------------------------------------
# Tanınmayan kasa
# -------------------------------------------------

def test_unknown_marker_returns_true_and_shows_banner(controller):

    _setup_two_models(controller, current_index=0)

    is_unknown = False

    for _ in range(controller.MARKER_SWITCH_CONFIRM_FRAMES):
        is_unknown = controller._handle_marker_model_detection(
            _result(99, results={"G01": {"state": "FULL"}})
        )

    assert is_unknown is True
    assert not controller.page.unknown_kasa_banner.isHidden()


def test_unknown_marker_saves_capture_with_roi_states(controller):

    _setup_two_models(controller, current_index=0)

    for _ in range(controller.MARKER_SWITCH_CONFIRM_FRAMES):
        controller._handle_marker_model_detection(
            _result(
                99,
                results={
                    "G01": {"state": "FULL"}, "G02": {"state": "EMPTY"}
                }
            )
        )

    capture_dir = controller.current_band.root / "unknown_kasa_captures"
    assert capture_dir.is_dir()

    json_files = list(capture_dir.glob("*.json"))
    assert len(json_files) == 1

    metadata = json.loads(json_files[0].read_text(encoding="utf-8"))
    assert metadata["marker_id"] == 99
    assert metadata["roi_states"] == {"G01": "FULL", "G02": "EMPTY"}


def test_unknown_marker_does_not_resave_every_tick(controller):

    _setup_two_models(controller, current_index=0)

    for _ in range(controller.MARKER_SWITCH_CONFIRM_FRAMES + 5):
        controller._handle_marker_model_detection(_result(99))

    capture_dir = controller.current_band.root / "unknown_kasa_captures"
    json_files = list(capture_dir.glob("*.json"))

    assert len(json_files) == 1


def test_unknown_marker_sends_telegram_notification(controller, monkeypatch):

    _setup_two_models(controller, current_index=0)

    controller.telegram_settings_manager.save(
        TelegramSettings(bot_token="tok", chat_id="chat")
    )

    sent = []

    monkeypatch.setattr(
        TelegramNotifier,
        "send_message",
        lambda self, text: (sent.append(text), 1)[1]
    )

    for _ in range(controller.MARKER_SWITCH_CONFIRM_FRAMES):
        controller._handle_marker_model_detection(_result(99))

    assert len(sent) == 1
    assert "99" in sent[0]


def test_unknown_marker_notification_cooldown(controller, monkeypatch):

    _setup_two_models(controller, current_index=0)

    controller.telegram_settings_manager.save(
        TelegramSettings(bot_token="tok", chat_id="chat")
    )

    sent = []

    monkeypatch.setattr(
        TelegramNotifier,
        "send_message",
        lambda self, text: (sent.append(text), 1)[1]
    )

    for _ in range(controller.MARKER_SWITCH_CONFIRM_FRAMES + 5):
        controller._handle_marker_model_detection(_result(99))

    # yeni bir tanınmayan ID (77) görülse bile, cooldown süresi
    # dolmadığı için ikinci bir bildirim gitmemeli
    for _ in range(controller.MARKER_SWITCH_CONFIRM_FRAMES):
        controller._handle_marker_model_detection(_result(77))

    assert len(sent) == 1


def test_no_candidate_id_is_a_no_op(controller):

    _setup_two_models(controller, current_index=0)

    for _ in range(controller.MARKER_SWITCH_CONFIRM_FRAMES + 2):
        is_unknown = controller._handle_marker_model_detection(_result(None))

    assert is_unknown is False
    assert controller.current_model.marker_id == 0


def test_known_marker_after_unknown_switches_and_clears_banner(controller):

    _setup_two_models(controller, current_index=0)

    for _ in range(controller.MARKER_SWITCH_CONFIRM_FRAMES):
        controller._handle_marker_model_detection(_result(99))

    assert not controller.page.unknown_kasa_banner.isHidden()

    for _ in range(controller.MARKER_SWITCH_CONFIRM_FRAMES):
        controller._handle_marker_model_detection(_result(4))

    assert controller.current_model.marker_id == 4
    assert controller.page.unknown_kasa_banner.isHidden()
