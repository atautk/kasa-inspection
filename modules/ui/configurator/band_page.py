from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QLabel,
    QLineEdit,
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

        layout.addWidget(management_group)

        # ---------- Arduino (Demo/Sunum Amaçlı) ----------

        arduino_group = QGroupBox("Arduino Alarm (Demo)")
        arduino_layout = QHBoxLayout(arduino_group)

        arduino_layout.addWidget(QLabel("Port (örn. COM3):"))

        self.arduino_port_input = QLineEdit()
        self.arduino_port_input.setEnabled(False)
        arduino_layout.addWidget(self.arduino_port_input)

        self.save_arduino_button = QPushButton("Kaydet")
        self.save_arduino_button.setEnabled(False)
        arduino_layout.addWidget(self.save_arduino_button)

        layout.addWidget(arduino_group)

    # -------------------------------------------------
    # Arduino Portu
    # -------------------------------------------------

    def set_arduino_port(self, value: str):

        self.arduino_port_input.setText(value or "")

    def get_arduino_port(self) -> str:

        return self.arduino_port_input.text().strip()

    def enable_arduino_controls(self, enabled: bool):

        self.arduino_port_input.setEnabled(enabled)
        self.save_arduino_button.setEnabled(enabled)
