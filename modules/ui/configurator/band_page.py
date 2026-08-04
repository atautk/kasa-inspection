from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QLabel,
    QComboBox,
    QGroupBox
)


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

        layout.addWidget(management_group)

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
