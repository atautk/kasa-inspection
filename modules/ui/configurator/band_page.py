from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLabel,
    QComboBox,
    QGroupBox
)
from PySide6.QtCore import Qt


class BandPage(QWidget):

    def __init__(self):

        super().__init__()

        layout = QVBoxLayout(self)

        title = QLabel("Bandlar")
        layout.addWidget(title)

        self.band_list = QListWidget()
        layout.addWidget(self.band_list)

        # ---------- Günlük Kullanım ----------

        daily_row = QHBoxLayout()

        self.new_button = QPushButton("Yeni Band")
        daily_row.addWidget(self.new_button)

        self.open_button = QPushButton("Bandı Aç")
        daily_row.addWidget(self.open_button)

        layout.addLayout(daily_row)

        # ---------- Yönetim (Doğrulama / Dışa-İçe Aktarma / Operatör) ----------

        management_group = QGroupBox("Yönetim")
        management_layout = QVBoxLayout(management_group)

        self.validate_button = QPushButton("Doğrula")
        management_layout.addWidget(self.validate_button)

        export_row = QHBoxLayout()

        self.export_button = QPushButton("Dışa Aktar")
        export_row.addWidget(self.export_button)

        self.import_button = QPushButton("İçe Aktar")
        export_row.addWidget(self.import_button)

        management_layout.addLayout(export_row)

        self.manage_operators_button = QPushButton("Operatörleri Yönet")
        management_layout.addWidget(self.manage_operators_button)

        self.audit_log_button = QPushButton("Giriş/Çıkış ve Değişiklik Logu")
        management_layout.addWidget(self.audit_log_button)

        self.telegram_settings_button = QPushButton("Telegram Bildirimleri")
        management_layout.addWidget(self.telegram_settings_button)

        self.telegram_recipients_button = QPushButton(
            "Bildirim Alıcıları (Telefon Numarası)"
        )
        management_layout.addWidget(self.telegram_recipients_button)

        layout.addWidget(management_group)

        # ---------- Kamera Kanalları (Çoklu Açı) ----------
        # Aynı kasayı farklı açılardan izlemek için birincil kameraya
        # ek kameralar tanımlanabilir. Bandın kendisinin camera/
        # reference/roi alanları "birincil" kamerayı temsil eder ve
        # buradan etkilenmez.

        camera_channels_group = QGroupBox(
            "Kamera Kanalları (Çoklu Açı)"
        )
        camera_channels_layout = QVBoxLayout(camera_channels_group)

        self.camera_channel_list = QListWidget()
        camera_channels_layout.addWidget(self.camera_channel_list)

        camera_channel_buttons = QHBoxLayout()

        self.add_camera_channel_button = QPushButton("Kanal Ekle")
        self.add_camera_channel_button.setEnabled(False)
        camera_channel_buttons.addWidget(self.add_camera_channel_button)

        self.remove_camera_channel_button = QPushButton("Kanal Sil")
        self.remove_camera_channel_button.setEnabled(False)
        camera_channel_buttons.addWidget(self.remove_camera_channel_button)

        camera_channels_layout.addLayout(camera_channel_buttons)

        layout.addWidget(camera_channels_group)

        # ---------- Arduino (Demo/Sunum Amaçlı) ----------

        arduino_group = QGroupBox("Arduino Alarm (Demo)")
        arduino_layout = QHBoxLayout(arduino_group)

        arduino_layout.addWidget(QLabel("Port:"))

        self.arduino_port_combo = QComboBox()
        self.arduino_port_combo.setEditable(True)
        self.arduino_port_combo.setEnabled(False)
        arduino_layout.addWidget(self.arduino_port_combo)

        self.refresh_ports_button = QPushButton("Portları Yenile")
        self.refresh_ports_button.setEnabled(False)
        arduino_layout.addWidget(self.refresh_ports_button)

        self.save_arduino_button = QPushButton("Kaydet")
        self.save_arduino_button.setEnabled(False)
        arduino_layout.addWidget(self.save_arduino_button)

        layout.addWidget(arduino_group)

    # -------------------------------------------------
    # Arduino Portu
    # -------------------------------------------------

    def set_arduino_port(self, value: str):

        self.arduino_port_combo.setCurrentText(value or "")

    def get_arduino_port(self) -> str:

        return self.arduino_port_combo.currentText().strip()

    def set_available_ports(self, ports: list[str]):

        current = self.arduino_port_combo.currentText()

        self.arduino_port_combo.blockSignals(True)

        self.arduino_port_combo.clear()
        self.arduino_port_combo.addItems(ports)

        self.arduino_port_combo.setCurrentText(current)

        self.arduino_port_combo.blockSignals(False)

    def enable_arduino_controls(self, enabled: bool):

        self.arduino_port_combo.setEnabled(enabled)
        self.refresh_ports_button.setEnabled(enabled)
        self.save_arduino_button.setEnabled(enabled)

    # -------------------------------------------------
    # Kamera Kanalları
    # -------------------------------------------------

    def set_camera_channels(self, channels: list):
        """
        channels: [{"id": ..., "name": ..., "camera_index": ...}, ...]
        """

        self.camera_channel_list.clear()

        for channel in channels:

            item = QListWidgetItem(
                f"{channel['name']} (Kamera {channel['camera_index']})"
            )

            item.setData(Qt.UserRole, channel["id"])

            self.camera_channel_list.addItem(item)

    def get_selected_camera_channel_id(self):

        item = self.camera_channel_list.currentItem()

        if item is None:
            return None

        return item.data(Qt.UserRole)

    def enable_camera_channel_controls(self, enabled: bool):

        self.add_camera_channel_button.setEnabled(enabled)
        self.remove_camera_channel_button.setEnabled(enabled)
