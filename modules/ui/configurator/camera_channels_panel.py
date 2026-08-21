from PySide6.QtWidgets import (
    QWidget,
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


class CameraChannelsPanel(QWidget):
    """
    Bir bandın ek kamera kanallarını (aynı kasayı farklı açılardan
    izleyen kameralar) ekleme/silme paneli. Reference/ROI
    sekmelerindeki kanal seçim kutuları değiştikten sonra yeniden
    okunmalıdır - bkz. on_channels_changed. Ayarlar penceresi içine
    gömülür - bkz. SettingsDialog.
    """

    def __init__(self, band_manager, band, on_channels_changed=None, parent=None):

        super().__init__(parent)

        self.band_manager = band_manager
        self.band = band
        self.on_channels_changed = on_channels_changed

        layout = QVBoxLayout(self)

        title = QLabel("Kamera Kanalları")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        info_label = QLabel(
            "Aynı kasayı farklı açılardan izlemek için ek kamera "
            "kanalları tanımlayın. Her kanalın kendi referans "
            "fotoğrafı ve göz seti olur (Referans/Gözler sekmelerinde "
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

        layout.addLayout(button_row)

        self.set_band(band)

    # -------------------------------------------------

    def set_band(self, band):

        self.band = band
        self._reload_list()

    def _reload_list(self):

        self.channel_list.clear()

        if self.band is None:
            return

        for channel in self.band.cameras:

            item = QListWidgetItem(
                f"{channel.name} (Kamera {channel.camera_index})"
            )

            item.setData(Qt.UserRole, channel.id)

            self.channel_list.addItem(item)

    # -------------------------------------------------

    def _on_add_clicked(self):

        if self.band is None:
            return

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

        if self.on_channels_changed is not None:
            self.on_channels_changed()

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
            "Kamera kanalı silinecek (fotoğraf/göz dosyaları diskte "
            "kalır ama band artık onları kullanmaz). Devam edilsin mi?"
        )

        if answer != QMessageBox.Yes:
            return

        self.band_manager.remove_camera_channel(
            self.band,
            item.data(Qt.UserRole)
        )

        self._reload_list()

        if self.on_channels_changed is not None:
            self.on_channels_changed()
