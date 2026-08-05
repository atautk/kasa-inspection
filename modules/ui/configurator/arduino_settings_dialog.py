from serial.tools import list_ports

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton
)

from ..window_utils import restore_or_center, save_geometry

SETTINGS_KEY = "arduino_settings_dialog"


class ArduinoSettingsDialog(QDialog):
    """
    Bir bandın Arduino alarm portunu seçme/kaydetme penceresi
    (demo/sunum amaçlı donanım entegrasyonu).

    Kaydetme işini kendisi yapmaz - "Kaydet" butonuna basılınca
    accept() ile kapanır, gerçek kaydetme işini çağıran
    (ConfiguratorController.open_arduino_settings) get_port() ile
    okuyup yapar.
    """

    def __init__(self, current_port: str, parent=None):

        super().__init__(parent)

        self.setWindowTitle("Arduino Ayarları")
        self.setModal(True)
        restore_or_center(self, SETTINGS_KEY, 420, 160)

        layout = QVBoxLayout(self)

        port_row = QHBoxLayout()

        port_row.addWidget(QLabel("Port:"))

        self.port_combo = QComboBox()
        self.port_combo.setEditable(True)
        self.port_combo.setCurrentText(current_port or "")
        port_row.addWidget(self.port_combo, stretch=1)

        layout.addLayout(port_row)

        self.refresh_button = QPushButton("Portları &Yenile")
        self.refresh_button.clicked.connect(self._refresh_ports)
        layout.addWidget(self.refresh_button)

        button_row = QHBoxLayout()

        button_row.addStretch()

        self.cancel_button = QPushButton("İptal")
        self.cancel_button.clicked.connect(self.reject)
        button_row.addWidget(self.cancel_button)

        self.save_button = QPushButton("&Kaydet")
        self.save_button.clicked.connect(self.accept)
        button_row.addWidget(self.save_button)

        layout.addLayout(button_row)

        self._refresh_ports()
        self.port_combo.setCurrentText(current_port or "")

    # -------------------------------------------------

    def closeEvent(self, event):

        save_geometry(self, SETTINGS_KEY)

        super().closeEvent(event)

    # -------------------------------------------------

    def get_port(self) -> str:

        return self.port_combo.currentText().strip()

    # -------------------------------------------------

    def _refresh_ports(self):

        current = self.port_combo.currentText()

        self.port_combo.blockSignals(True)

        self.port_combo.clear()
        self.port_combo.addItems(
            [p.device for p in list_ports.comports()]
        )

        self.port_combo.setCurrentText(current)

        self.port_combo.blockSignals(False)
