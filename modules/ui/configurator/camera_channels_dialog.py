from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QInputDialog,
    QMessageBox
)
from PySide6.QtCore import Qt

from ..window_utils import restore_or_center, save_geometry

SETTINGS_KEY = "camera_channels_dialog"


class CameraChannelsDialog(QDialog):
    """
    Bir bandın ek kamera kanallarını (aynı kasayı farklı açılardan
    izleyen kameralar) ekleme/silme penceresi. Reference/ROI
    sekmelerindeki kanal seçim kutuları, bu pencere kapandığında
    yeniden okunmalıdır - bkz. ConfiguratorController.open_camera_channels.
    """

    def __init__(self, band_manager, band, parent=None):

        super().__init__(parent)

        self.band_manager = band_manager
        self.band = band

        self.setWindowTitle(f"Kamera Kanalları - {band.name}")
        self.setModal(True)
        restore_or_center(self, SETTINGS_KEY, 480, 400)

        layout = QVBoxLayout(self)

        info_label = QLabel(
            "Aynı kasayı farklı açılardan izlemek için ek kamera "
            "kanalları tanımlayın. Her kanalın kendi referans "
            "fotoğrafı ve ROI seti olur (Reference/ROI sekmelerinde "
            "kanal seçilerek düzenlenir)."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray;")
        layout.addWidget(info_label)

        self.channel_list = QListWidget()
        layout.addWidget(self.channel_list)

        button_row = QHBoxLayout()

        self.add_button = QPushButton("&Kanal Ekle")
        self.add_button.clicked.connect(self._on_add_clicked)
        button_row.addWidget(self.add_button)

        self.remove_button = QPushButton("Kanal &Sil")
        self.remove_button.clicked.connect(self._on_remove_clicked)
        button_row.addWidget(self.remove_button)

        button_row.addStretch()

        self.close_button = QPushButton("&Kapat")
        self.close_button.clicked.connect(self.accept)
        button_row.addWidget(self.close_button)

        layout.addLayout(button_row)

        self._reload_list()

    # -------------------------------------------------

    def closeEvent(self, event):

        save_geometry(self, SETTINGS_KEY)

        super().closeEvent(event)

    # -------------------------------------------------

    def _reload_list(self):

        self.channel_list.clear()

        for channel in self.band.cameras:

            item = QListWidgetItem(
                f"{channel.name} (Kamera {channel.camera_index})"
            )

            item.setData(Qt.UserRole, channel.id)

            self.channel_list.addItem(item)

    # -------------------------------------------------

    def _on_add_clicked(self):

        name, ok = QInputDialog.getText(
            self,
            "Yeni Kamera Kanalı",
            "Kanal Adı (ör. Yan, Üst)"
        )

        if not ok:
            return

        name = name.strip()

        if name == "":
            return

        camera_index, ok = QInputDialog.getInt(
            self,
            "Yeni Kamera Kanalı",
            "Kamera İndeksi",
            0,
            0,
            16
        )

        if not ok:
            return

        self.band_manager.add_camera_channel(self.band, name, camera_index)

        self._reload_list()

    # -------------------------------------------------

    def _on_remove_clicked(self):

        item = self.channel_list.currentItem()

        if item is None:

            QMessageBox.warning(
                self,
                "Uyarı",
                "Lütfen silinecek bir kamera kanalı seçin."
            )

            return

        answer = QMessageBox.question(
            self,
            "Emin misiniz?",
            "Kamera kanalı silinecek (fotoğraf/ROI dosyaları diskte "
            "kalır ama band artık onları kullanmaz). Devam edilsin mi?"
        )

        if answer != QMessageBox.Yes:
            return

        self.band_manager.remove_camera_channel(
            self.band,
            item.data(Qt.UserRole)
        )

        self._reload_list()
