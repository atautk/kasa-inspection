from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget
)

from .band_page import BandPage
from .reference_page import ReferencePage
from .roi_page import ROIPage
from .model_page import ModelPage


class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("KASA CONFIGURATOR")

        self.resize(1400, 900)

        self.tabs = QTabWidget()

        self.band_page = BandPage()
        self.reference_page = ReferencePage()
        self.roi_page = ROIPage()
        self.model_page = ModelPage()

        self.tabs.addTab(self.band_page, "Band")
        self.tabs.addTab(self.reference_page, "Reference")
        self.tabs.addTab(self.roi_page, "ROI")
        self.tabs.addTab(self.model_page, "Models")

        self.tabs.setTabEnabled(1, False)
        self.tabs.setTabEnabled(2, False)
        self.tabs.setTabEnabled(3, False)

        self.setCentralWidget(self.tabs)