import pytest


@pytest.fixture(scope="module")
def qapp():

    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


@pytest.fixture
def widgets():
    """
    Testin oluşturduğu pencereleri toplar ve test bitince kapatır -
    bkz. tests/conftest.py ve test_page_resize_scaling.py'deki aynı
    desen.
    """

    created = []

    yield created

    for widget in created:
        widget.close()


def _make_widget(qapp, widgets):

    from PySide6.QtWidgets import QWidget

    widget = QWidget()
    widgets.append(widget)
    return widget


def test_clamp_to_screen_shrinks_oversized_window(qapp, widgets):

    from PySide6.QtGui import QGuiApplication
    from modules.ui.window_utils import _clamp_to_screen

    screen = QGuiApplication.primaryScreen()

    if screen is None:
        pytest.skip("Ekran bilgisi olmadan test edilemez")

    available = screen.availableGeometry()

    widget = _make_widget(qapp, widgets)
    widget.resize(available.width() + 500, available.height() + 500)
    widget.show()

    _clamp_to_screen(widget)

    assert widget.width() <= available.width()
    assert widget.height() <= available.height()


def test_clamp_to_screen_repositions_offscreen_window(qapp, widgets):

    from PySide6.QtGui import QGuiApplication
    from modules.ui.window_utils import _clamp_to_screen

    screen = QGuiApplication.primaryScreen()

    if screen is None:
        pytest.skip("Ekran bilgisi olmadan test edilemez")

    available = screen.availableGeometry()

    widget = _make_widget(qapp, widgets)
    widget.resize(400, 300)
    widget.move(-5000, -5000)
    widget.show()

    _clamp_to_screen(widget)

    geo = widget.frameGeometry()

    assert geo.x() >= available.x()
    assert geo.y() >= available.y()
    assert geo.x() + geo.width() <= available.x() + available.width()
    assert geo.y() + geo.height() <= available.y() + available.height()


def test_restore_or_center_clamps_saved_offscreen_geometry(
    qapp, widgets, tmp_path, monkeypatch
):
    """
    Farklı bir ekran/çözünürlükte kaydedilmiş (ör. artık bağlı
    olmayan ikinci monitörde) bir geometri geri yüklendiğinde,
    pencere ekrandan taşmadan mevcut ekrana sığdırılmalı.
    """

    from PySide6.QtCore import QSettings
    from PySide6.QtGui import QGuiApplication
    import modules.ui.window_utils as window_utils

    screen = QGuiApplication.primaryScreen()

    if screen is None:
        pytest.skip("Ekran bilgisi olmadan test edilemez")

    settings_path = tmp_path / "window_settings.ini"

    donor = _make_widget(qapp, widgets)
    donor.resize(400, 300)
    donor.move(-9000, -9000)
    donor.show()

    settings = QSettings(str(settings_path), QSettings.IniFormat)
    settings.setValue("test_key/geometry", donor.saveGeometry())
    settings.sync()

    monkeypatch.setattr(
        window_utils,
        "get_app_settings",
        lambda: QSettings(str(settings_path), QSettings.IniFormat)
    )

    target = _make_widget(qapp, widgets)

    window_utils.restore_or_center(target, "test_key", 400, 300)

    available = screen.availableGeometry()
    geo = target.frameGeometry()

    assert geo.x() >= available.x()
    assert geo.y() >= available.y()
    assert geo.x() + geo.width() <= available.x() + available.width()
    assert geo.y() + geo.height() <= available.y() + available.height()
