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


@pytest.fixture(autouse=True)
def _no_blocking_dialogs():
    """
    save_model() basarili yolda gercek (mocklanmamis) bir
    QMessageBox.information() acar - bu, offscreen Qt platform'unda
    testleri ciddi sekilde yavaslatiyordu (5 test ~140s). Basari
    bildirimini her testte ayri ayri mocklamak yerine, burada tek
    seferde susturuyoruz.
    """

    with patch(
        "modules.ui.configurator.configurator_controller."
        "QMessageBox.information"
    ):
        yield


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


def _create_and_select_model(controller, name):

    controller.model_manager.create_model(controller.current_band, name)
    controller.load_model_tab()

    page = controller.window.model_page

    for row in range(page.model_list.count()):

        item = page.model_list.item(row)

        if item.text() == name:
            page.model_list.setCurrentItem(item)
            break

    return controller.current_model


def test_marker_id_saves_successfully(controller):

    _open_band(controller)
    _create_and_select_model(controller, "Model A")

    controller.window.model_page.marker_id_input.setValue(4)

    controller.save_model()

    reloaded = controller.model_manager.load_model(
        controller.current_band, controller.current_model.id
    )
    assert reloaded.marker_id == 4


def test_special_value_minus_one_saves_as_none(controller):

    _open_band(controller)
    _create_and_select_model(controller, "Model A")

    controller.window.model_page.marker_id_input.setValue(-1)

    controller.save_model()

    reloaded = controller.model_manager.load_model(
        controller.current_band, controller.current_model.id
    )
    assert reloaded.marker_id is None


def test_reserved_corner_id_is_rejected(controller):

    _open_band(controller)
    _create_and_select_model(controller, "Model A")

    controller.window.model_page.marker_id_input.setValue(2)

    with patch(
        "modules.ui.configurator.configurator_controller.QMessageBox.warning"
    ) as mock_warning:

        controller.save_model()

    assert mock_warning.called

    reloaded = controller.model_manager.load_model(
        controller.current_band, controller.current_model.id
    )
    assert reloaded.marker_id is None


def test_duplicate_marker_id_across_models_is_rejected(controller):

    _open_band(controller)

    model_a = _create_and_select_model(controller, "Model A")
    controller.window.model_page.marker_id_input.setValue(4)
    controller.save_model()

    _create_and_select_model(controller, "Model B")
    controller.window.model_page.marker_id_input.setValue(4)

    with patch(
        "modules.ui.configurator.configurator_controller.QMessageBox.warning"
    ) as mock_warning:

        controller.save_model()

    assert mock_warning.called

    reloaded_b = controller.model_manager.load_model(
        controller.current_band, controller.current_model.id
    )
    assert reloaded_b.marker_id is None

    reloaded_a = controller.model_manager.load_model(
        controller.current_band, model_a.id
    )
    assert reloaded_a.marker_id == 4


def test_same_model_keeping_its_own_marker_id_is_allowed(controller):

    _open_band(controller)
    _create_and_select_model(controller, "Model A")

    controller.window.model_page.marker_id_input.setValue(4)
    controller.save_model()

    # Aynı modeli tekrar kaydet - kendi marker ID'siyle çakışma
    # sayılmamalı.
    controller.save_model()

    reloaded = controller.model_manager.load_model(
        controller.current_band, controller.current_model.id
    )
    assert reloaded.marker_id == 4
