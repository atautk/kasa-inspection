from unittest.mock import patch

import pytest

from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import Qt


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

    # open_band() sonunda gerçek (mock'lanmamış) bir QMessageBox.information
    # modal'ı açar - bu testte gösterilecek gerçek bir kullanıcı olmadığından
    # bastırılmazsa donmaya/native çökmeye yol açabiliyor.
    with patch(
        "modules.ui.configurator.configurator_controller."
        "QMessageBox.information"
    ):
        controller.open_band()

    return controller.current_band


def _select_band_by_name(controller, name):

    page = controller.window.band_page

    for i in range(page.band_list.count()):

        item = page.band_list.item(i)

        if item.text() == name:
            page.band_list.setCurrentItem(item)
            return item

    return None


# -------------------------------------------------
# Yeniden Adlandırma
# -------------------------------------------------


def test_rename_warns_when_no_band_selected(controller):

    with patch(
        "modules.ui.configurator.configurator_controller.QMessageBox.warning"
    ) as mock_warning:

        controller.rename_band()

    assert mock_warning.called


def test_rename_updates_name_and_persists(controller):

    controller.band_manager.create_band("Eski İsim")
    controller.load_bands()

    _select_band_by_name(controller, "Eski İsim")

    with patch(
        "modules.ui.configurator.configurator_controller.QInputDialog.getText",
        return_value=("Yeni İsim", True)
    ):

        controller.rename_band()

    names = [
        controller.window.band_page.band_list.item(i).text()
        for i in range(controller.window.band_page.band_list.count())
    ]

    assert "Yeni İsim" in names
    assert "Eski İsim" not in names


def test_rename_cancelled_dialog_does_not_change_name(controller):

    controller.band_manager.create_band("Değişmeyen")
    controller.load_bands()

    _select_band_by_name(controller, "Değişmeyen")

    with patch(
        "modules.ui.configurator.configurator_controller.QInputDialog.getText",
        return_value=("Yeni İsim", False)
    ):

        controller.rename_band()

    names = [
        controller.window.band_page.band_list.item(i).text()
        for i in range(controller.window.band_page.band_list.count())
    ]

    assert "Değişmeyen" in names


def test_rename_empty_name_is_ignored(controller):

    controller.band_manager.create_band("Boş Olmayan")
    controller.load_bands()

    _select_band_by_name(controller, "Boş Olmayan")

    with patch(
        "modules.ui.configurator.configurator_controller.QInputDialog.getText",
        return_value=("   ", True)
    ):

        controller.rename_band()

    names = [
        controller.window.band_page.band_list.item(i).text()
        for i in range(controller.window.band_page.band_list.count())
    ]

    assert "Boş Olmayan" in names


def test_rename_updates_open_band_window_title(controller):

    band = _open_band(controller, "Açık Band")

    _select_band_by_name(controller, "Açık Band")

    with patch(
        "modules.ui.configurator.configurator_controller.QInputDialog.getText",
        return_value=("Yeni Açık Ad", True)
    ):

        controller.rename_band()

    assert controller.current_band.name == "Yeni Açık Ad"
    assert "Yeni Açık Ad" in controller.window.windowTitle()


# -------------------------------------------------
# Silme
# -------------------------------------------------


def test_delete_warns_when_no_band_selected(controller):

    with patch(
        "modules.ui.configurator.configurator_controller.QMessageBox.warning"
    ) as mock_warning:

        controller.delete_band()

    assert mock_warning.called


def test_delete_asks_for_confirmation_and_removes_band(controller):

    controller.band_manager.create_band("Silinecek Band")
    controller.load_bands()

    _select_band_by_name(controller, "Silinecek Band")

    with patch(
        "modules.ui.configurator.configurator_controller.QMessageBox.question",
        return_value=QMessageBox.Yes
    ) as mock_question:

        controller.delete_band()

    assert mock_question.called

    names = [
        controller.window.band_page.band_list.item(i).text()
        for i in range(controller.window.band_page.band_list.count())
    ]

    assert "Silinecek Band" not in names


def test_delete_declined_confirmation_keeps_band(controller):

    controller.band_manager.create_band("Kalacak Band")
    controller.load_bands()

    _select_band_by_name(controller, "Kalacak Band")

    with patch(
        "modules.ui.configurator.configurator_controller.QMessageBox.question",
        return_value=QMessageBox.No
    ):

        controller.delete_band()

    names = [
        controller.window.band_page.band_list.item(i).text()
        for i in range(controller.window.band_page.band_list.count())
    ]

    assert "Kalacak Band" in names


def test_delete_removes_band_folder_from_disk(controller, tmp_path):

    controller.band_manager.create_band("Disk Testi")
    controller.load_bands()

    item = _select_band_by_name(controller, "Disk Testi")
    band_id = item.data(Qt.UserRole)

    with patch(
        "modules.ui.configurator.configurator_controller.QMessageBox.question",
        return_value=QMessageBox.Yes
    ):

        controller.delete_band()

    assert not controller.band_manager.exists(band_id)


def test_delete_currently_open_band_is_blocked(controller):

    _open_band(controller, "Açık Band")

    _select_band_by_name(controller, "Açık Band")

    with patch(
        "modules.ui.configurator.configurator_controller.QMessageBox.warning"
    ) as mock_warning, patch(
        "modules.ui.configurator.configurator_controller.QMessageBox.question"
    ) as mock_question:

        controller.delete_band()

    assert mock_warning.called
    assert not mock_question.called

    names = [
        controller.window.band_page.band_list.item(i).text()
        for i in range(controller.window.band_page.band_list.count())
    ]

    assert "Açık Band" in names
