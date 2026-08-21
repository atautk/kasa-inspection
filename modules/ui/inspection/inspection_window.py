from PySide6.QtWidgets import QMainWindow

from .inspection_page import InspectionPage
from ..common.accessibility_dialog import AccessibilityDialog

from ..window_utils import restore_or_center, save_geometry

SETTINGS_KEY = "inspection_main"


class InspectionWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("KASA İNCELEME")

        restore_or_center(self, SETTINGS_KEY, 1500, 900)

        self.inspection_page = InspectionPage()

        self.setCentralWidget(self.inspection_page)

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
