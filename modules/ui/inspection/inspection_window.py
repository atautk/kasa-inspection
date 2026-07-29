from PySide6.QtWidgets import QMainWindow

from .inspection_page import InspectionPage


class InspectionWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("KASA INSPECTION")

        self.resize(1500, 900)

        self.inspection_page = InspectionPage()

        self.setCentralWidget(self.inspection_page)
