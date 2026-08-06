import numpy as np
import pytest
from unittest.mock import patch

from PySide6.QtWidgets import QMessageBox


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

    from modules.ui.configurator.main_window import MainWindow
    from modules.ui.configurator.configurator_controller import (
        ConfiguratorController
    )
    from modules.configuration.band_manager import BandManager

    window = MainWindow()
    ctrl = ConfiguratorController(window, operator_name="test")

    ctrl.band_manager = BandManager(root=tmp_path / "configuration")

    yield ctrl

    window.close()


def _open_band(controller, name="Test Bandı"):

    controller.band_manager.create_band(name)
    controller.load_bands()

    item = controller.window.band_page.band_list.item(0)
    controller.window.band_page.band_list.setCurrentItem(item)

    controller.open_band()

    return controller.current_band


def _sharp_frame():

    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    frame[::10, :] = 255
    frame[:, ::10] = 255

    return frame


def _blurry_frame():

    return np.full((200, 200, 3), 128, dtype=np.uint8)


def test_sharp_reference_saves_without_confirmation(controller):

    band = _open_band(controller)

    controller.last_reference_frame = _sharp_frame()

    with patch(
        "modules.ui.configurator.configurator_controller.QMessageBox.question"
    ) as mock_question:

        controller.capture_reference()

    assert not mock_question.called
    assert controller.reference_manager.exists(band)


def test_blurry_reference_asks_for_confirmation(controller):

    band = _open_band(controller)

    controller.last_reference_frame = _blurry_frame()

    with patch(
        "modules.ui.configurator.configurator_controller.QMessageBox.question",
        return_value=QMessageBox.Yes
    ) as mock_question:

        controller.capture_reference()

    assert mock_question.called
    assert controller.reference_manager.exists(band)


def test_blurry_reference_not_saved_if_user_declines(controller):

    band = _open_band(controller)

    controller.last_reference_frame = _blurry_frame()

    with patch(
        "modules.ui.configurator.configurator_controller.QMessageBox.question",
        return_value=QMessageBox.No
    ):

        controller.capture_reference()

    assert not controller.reference_manager.exists(band)
