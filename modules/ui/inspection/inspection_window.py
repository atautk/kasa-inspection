from PySide6.QtWidgets import QMainWindow

from .inspection_page import InspectionPage

from ..window_utils import restore_or_center, save_geometry

SETTINGS_KEY = "inspection_main"


class InspectionWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("KASA INSPECTION")

        restore_or_center(self, SETTINGS_KEY, 1500, 900)

        self.inspection_page = InspectionPage()

        self.setCentralWidget(self.inspection_page)

    # -------------------------------------------------

    def closeEvent(self, event):

        save_geometry(self, SETTINGS_KEY)

        super().closeEvent(event)
