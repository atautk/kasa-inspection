from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QLabel,
    QDoubleSpinBox,
    QLineEdit
)


class BandPage(QWidget):

    def __init__(self):

        super().__init__()

        layout = QVBoxLayout(self)

        title = QLabel("Bandlar")
        layout.addWidget(title)

        self.band_list = QListWidget()
        layout.addWidget(self.band_list)

        self.new_button = QPushButton("Yeni Band")
        layout.addWidget(self.new_button)

        self.open_button = QPushButton("Bandı Aç")
        layout.addWidget(self.open_button)

        self.validate_button = QPushButton("Doğrula")
        layout.addWidget(self.validate_button)

        # ---------- Dışa / İçe Aktar ----------

        export_row = QHBoxLayout()

        self.export_button = QPushButton("Dışa Aktar")
        export_row.addWidget(self.export_button)

        self.import_button = QPushButton("İçe Aktar")
        export_row.addWidget(self.import_button)

        layout.addLayout(export_row)

        # ---------- Eşik Ayarı ----------

        threshold_row = QHBoxLayout()

        threshold_row.addWidget(QLabel("Değişim Eşiği (%):"))

        self.threshold_spinbox = QDoubleSpinBox()
        self.threshold_spinbox.setRange(0.0, 100.0)
        self.threshold_spinbox.setDecimals(1)
        self.threshold_spinbox.setSingleStep(0.1)
        self.threshold_spinbox.setEnabled(False)
        threshold_row.addWidget(self.threshold_spinbox)

        layout.addLayout(threshold_row)

        # ---------- Arduino Ayarı ----------

        arduino_row = QHBoxLayout()

        arduino_row.addWidget(QLabel("Arduino Portu (örn. COM3):"))

        self.arduino_port_input = QLineEdit()
        self.arduino_port_input.setEnabled(False)
        arduino_row.addWidget(self.arduino_port_input)

        layout.addLayout(arduino_row)

        self.save_threshold_button = QPushButton("Ayarları Kaydet")
        self.save_threshold_button.setEnabled(False)
        layout.addWidget(self.save_threshold_button)

        # ---------- Operatör Yönetimi ----------

        self.add_operator_button = QPushButton("Operatör Ekle")
        layout.addWidget(self.add_operator_button)

    # -------------------------------------------------
    # Eşik Kontrolleri
    # -------------------------------------------------

    def set_threshold(self, value: float):

        self.threshold_spinbox.setValue(value)

    def get_threshold(self) -> float:

        return self.threshold_spinbox.value()

    def enable_threshold_controls(self, enabled: bool):

        self.threshold_spinbox.setEnabled(enabled)
        self.arduino_port_input.setEnabled(enabled)
        self.save_threshold_button.setEnabled(enabled)

    # -------------------------------------------------
    # Arduino Portu
    # -------------------------------------------------

    def set_arduino_port(self, value: str):

        self.arduino_port_input.setText(value or "")

    def get_arduino_port(self) -> str:

        return self.arduino_port_input.text().strip()