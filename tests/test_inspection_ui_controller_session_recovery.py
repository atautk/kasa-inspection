from unittest.mock import MagicMock

import pytest

from modules.configuration.band_manager import BandManager


@pytest.fixture(scope="module")
def qapp():

    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


@pytest.fixture
def isolated_settings(tmp_path, monkeypatch):
    """
    get_app_settings() varsayılan olarak GERÇEK proje kökündeki
    window_settings.ini dosyasını kullanır. Bu testler was_running=True
    gibi FONKSİYONEL bir durumu yazıyor - eğer gerçek dosyaya sızarsa,
    geliştiricinin bir sonraki gerçek Inspection açılışında beklenmedik
    şekilde otomatik başlamasına yol açabilir. Bu yüzden her test kendi
    geçici dosyasını kullanmalı.
    """

    from PySide6.QtCore import QSettings

    settings_path = tmp_path / "test_window_settings.ini"

    def fake_get_app_settings():
        return QSettings(str(settings_path), QSettings.IniFormat)

    monkeypatch.setattr(
        "modules.ui.inspection.controller_mixins.session_recovery_mixin."
        "get_app_settings",
        fake_get_app_settings
    )

    return settings_path


@pytest.fixture
def controller(qapp, tmp_path, isolated_settings):

    from modules.ui.inspection.inspection_window import InspectionWindow
    from modules.ui.inspection.inspection_ui_controller import (
        InspectionUIController
    )

    window = InspectionWindow()

    # __init__ kendi _load_bands()'ini çağırır - henüz hiç band yokken
    # (isolated_settings zaten boş) bu zararsızca "band yok" der.
    ctrl = InspectionUIController(window, root=tmp_path, operator_name="test")

    ctrl.band_manager = BandManager(root=tmp_path / "configuration")

    yield ctrl

    window.close()


def _fake_camera():

    cap = MagicMock()
    cap.isOpened.return_value = True
    cap.read.return_value = (True, MagicMock())

    return cap


# -------------------------------------------------
# Kalıcı oturum durumu okuma/yazma
# -------------------------------------------------

def test_selecting_band_persists_last_band_id(controller):

    band = controller.band_manager.create_band("Clio Hattı")
    controller.bands = [band]
    controller.page.set_band_list([band.name])

    controller._select_band(0)

    state = controller._load_session_state()
    assert state["last_band_id"] == band.id


def test_selecting_model_persists_last_model_id(controller):

    band = controller.band_manager.create_band("Clio Hattı")
    controller.current_band = band

    from modules.configuration.model import Model

    model = Model(id="m1", name="Model 1", expected_rois=[])
    controller.models = [model]
    controller.page.set_model_list([model.name])

    controller._select_model(0)

    state = controller._load_session_state()
    assert state["last_model_id"] == "m1"


def test_starting_persists_was_running_true(controller, monkeypatch):

    band = controller.band_manager.create_band("Clio Hattı")
    controller.bands = [band]
    controller.page.set_band_list([band.name])
    controller._select_band(0)

    monkeypatch.setattr(
        controller, "_open_camera", lambda index: _fake_camera()
    )

    controller._start()

    assert controller._load_session_state()["was_running"] is True


def test_stopping_persists_was_running_false(controller, monkeypatch):

    band = controller.band_manager.create_band("Clio Hattı")
    controller.bands = [band]
    controller.page.set_band_list([band.name])
    controller._select_band(0)

    monkeypatch.setattr(
        controller, "_open_camera", lambda index: _fake_camera()
    )

    controller._start()
    controller._stop()

    assert controller._load_session_state()["was_running"] is False


def test_camera_failure_does_not_persist_was_running_true(
    controller, monkeypatch
):

    band = controller.band_manager.create_band("Clio Hattı")
    controller.bands = [band]
    controller.page.set_band_list([band.name])
    controller._select_band(0)

    monkeypatch.setattr(controller, "_open_camera", lambda index: None)
    monkeypatch.setattr(
        "modules.ui.inspection.inspection_ui_controller.QMessageBox.warning",
        lambda *a, **kw: None
    )

    controller._start()

    assert controller._load_session_state()["was_running"] is False


# -------------------------------------------------
# Index bulma yardımcıları
# -------------------------------------------------

def test_index_of_band_id_finds_match(controller):

    band1 = controller.band_manager.create_band("Clio Hattı")
    band2 = controller.band_manager.create_band("Duster Hattı")
    controller.bands = [band1, band2]

    assert controller._index_of_band_id(band2.id) == 1


def test_index_of_band_id_returns_none_when_not_found(controller):

    band = controller.band_manager.create_band("Clio Hattı")
    controller.bands = [band]

    assert controller._index_of_band_id("does-not-exist") is None


def test_index_of_band_id_returns_none_for_none_input(controller):

    assert controller._index_of_band_id(None) is None


# -------------------------------------------------
# _load_bands(): son kullanılan band/model'i önceliklendirme
# -------------------------------------------------

def test_load_bands_prefers_last_used_band_over_first(
    controller, isolated_settings
):

    band1 = controller.band_manager.create_band("Clio Hattı")
    band2 = controller.band_manager.create_band("Duster Hattı")

    # Duster'ı "son kullanılan" olarak simüle et
    controller.bands = [band1, band2]
    controller._select_band(1)

    # Yeniden yükleme simülasyonu (yeni bir uygulama başlangıcı gibi)
    controller._load_bands()

    assert controller.current_band.id == band2.id


def test_load_bands_falls_back_to_first_when_last_band_deleted(
    controller
):

    band1 = controller.band_manager.create_band("Clio Hattı")
    band2 = controller.band_manager.create_band("Duster Hattı")

    controller.bands = [band1, band2]
    controller._select_band(1)

    controller.band_manager.delete_band(band2.id)

    controller._load_bands()

    assert controller.current_band.id == band1.id


def test_load_bands_auto_starts_when_was_running(controller, monkeypatch):

    band = controller.band_manager.create_band("Clio Hattı")
    controller.bands = [band]
    controller._select_band(0)

    monkeypatch.setattr(
        controller, "_open_camera", lambda index: _fake_camera()
    )

    controller._start()
    controller.running = False  # _load_bands'in _start()'ı çağırdığını
    # ayırt edebilmek için önce sıfırlıyoruz (was_running zaten
    # ayarlarda True olarak kaldı)

    controller._load_bands()

    assert controller.running is True


def test_load_bands_does_not_auto_start_when_not_running(
    controller, monkeypatch
):

    band = controller.band_manager.create_band("Clio Hattı")
    controller.bands = [band]
    controller._select_band(0)

    start_calls = []
    monkeypatch.setattr(controller, "_start", lambda: start_calls.append(1))

    controller._load_bands()

    assert start_calls == []
    assert controller.running is False


def test_load_bands_with_no_bands_does_not_raise(controller):

    controller.bands = []

    controller._load_bands()

    assert controller.current_band is None or controller.bands == []
