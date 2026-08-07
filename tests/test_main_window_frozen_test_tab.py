import pytest


@pytest.fixture(scope="module")
def qapp():

    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


def _tab_titles(window) -> list:

    return [
        window.tabs.tabText(i) for i in range(window.tabs.count())
    ]


def test_dev_mode_shows_test_tab(qapp, monkeypatch):

    import sys
    from modules.ui.configurator import main_window as main_window_module

    monkeypatch.setattr(sys, "frozen", False, raising=False)

    window = main_window_module.MainWindow()

    try:
        assert "Testler" in _tab_titles(window)
    finally:
        window.close()


def test_frozen_mode_hides_test_tab(qapp, monkeypatch):
    """
    Paketlenmiş .exe'de pytest/tests/ klasörü bulunmadığından bu
    sekme çalışmaz - bkz. modules/ui/configurator/main_window.py.
    """

    import sys
    from modules.ui.configurator import main_window as main_window_module

    monkeypatch.setattr(sys, "frozen", True, raising=False)

    window = main_window_module.MainWindow()

    try:

        assert "Testler" not in _tab_titles(window)

        # Sekme eklenmese de widget hala oluşturulur - configurator
        # controller sinyal bağlarken window.test_runner_page'e
        # erişiyor (bkz. configurator_controller.connect_signals).
        assert window.test_runner_page is not None

    finally:
        window.close()
