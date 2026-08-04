from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget
)

from .band_page import BandPage
from .reference_page import ReferencePage
from .roi_page import ROIPage
from .model_page import ModelPage
from .test_runner_page import TestRunnerPage
from ..common.accessibility_dialog import AccessibilityDialog

from ..window_utils import restore_or_center, save_geometry

SETTINGS_KEY = "configurator_main"


class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("KASA CONFIGURATOR")

        restore_or_center(self, SETTINGS_KEY, 1400, 900)

        self.tabs = QTabWidget()

        self.band_page = BandPage()
        self.reference_page = ReferencePage()
        self.roi_page = ROIPage()
        self.model_page = ModelPage()
        self.test_runner_page = TestRunnerPage()

        self.tabs.addTab(self.band_page, "Band")
        self.tabs.addTab(self.reference_page, "Reference")
        self.tabs.addTab(self.roi_page, "ROI")
        self.tabs.addTab(self.model_page, "Models")
        self.tabs.addTab(self.test_runner_page, "Testler")

        self.tabs.setTabEnabled(1, False)
        self.tabs.setTabEnabled(2, False)
        self.tabs.setTabEnabled(3, False)

        self.setCentralWidget(self.tabs)

        self.close_callback = None

        self._build_menu()

    # -------------------------------------------------

    def _build_menu(self):

        view_menu = self.menuBar().addMenu("&Görünüm")

        accessibility_action = view_menu.addAction(
            "&Erişebilirlik Ayarları..."
        )
        accessibility_action.triggered.connect(
            self._open_accessibility_dialog
        )

    def _open_accessibility_dialog(self):

        dialog = AccessibilityDialog(self)
        dialog.exec()

    # -------------------------------------------------

    def closeEvent(self, event):

        if self.close_callback is not None:
            self.close_callback()

        save_geometry(self, SETTINGS_KEY)

        super().closeEvent(event)