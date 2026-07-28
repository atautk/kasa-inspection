from PySide6.QtWidgets import (
    QInputDialog,
    QMessageBox,
    QListWidgetItem
)
from PySide6.QtCore import Qt

from modules.configuration.band_manager import BandManager


class ConfiguratorController:

    def __init__(self, window):

        self.window = window

        self.band_manager = BandManager()

        self.current_band = None

        self.connect_signals()

        self.load_bands()

    # -------------------------------------------------

    def connect_signals(self):

        page = self.window.band_page

        page.new_button.clicked.connect(
            self.create_band
        )

        page.open_button.clicked.connect(
            self.open_band
        )

    # -------------------------------------------------

    def load_bands(self):

        page = self.window.band_page

        page.band_list.clear()

        bands = self.band_manager.list_bands()

        for band in bands:

            item = QListWidgetItem(band.name)

            item.setData(Qt.UserRole, band.id)

            page.band_list.addItem(item)

    # -------------------------------------------------

    def create_band(self):

        name, ok = QInputDialog.getText(

            self.window,

            "Yeni Band",

            "Band Adı"

        )

        if not ok:
            return

        name = name.strip()

        if name == "":
            return

        self.band_manager.create_band(name)

        self.load_bands()

    # -------------------------------------------------

    def open_band(self):

        page = self.window.band_page

        item = page.band_list.currentItem()

        if item is None:

            QMessageBox.warning(

                self.window,

                "Uyarı",

                "Lütfen bir band seçin."

            )

            return

        band_id = item.data(Qt.UserRole)

        self.current_band = self.band_manager.load_band(band_id)

        self.window.setWindowTitle(

            f"KASA CONFIGURATOR - {self.current_band.name}"

        )

        self.window.tabs.setTabEnabled(1, True)

        self.window.tabs.setTabEnabled(2, True)

        self.window.tabs.setTabEnabled(3, True)

        QMessageBox.information(

            self.window,

            "Başarılı",

            f"{self.current_band.name} açıldı."

        )