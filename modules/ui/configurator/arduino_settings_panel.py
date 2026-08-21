from serial.tools import list_ports

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton
)

from modules.utils.logger import get_logger

app_logger = get_logger()


class ArduinoSettingsPanel(QWidget):
    """
    Bir bandın Arduino alarm portunu seçme/kaydetme paneli (demo/
    sunum amaçlı donanım entegrasyonu). Ayarlar penceresi içine
    gömülür - bkz. SettingsDialog.
    """

    def __init__(self, band_manager, band, operator_name, parent=None):

        super().__init__(parent)

        self.band_manager = band_manager
        self.band = band
        self.operator_name = operator_name

        layout = QVBoxLayout(self)

        title = QLabel("Arduino Ayarları")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        port_row = QHBoxLayout()

        port_row.addWidget(QLabel("Port:"))

        self.port_combo = QComboBox()
        self.port_combo.setEditable(True)
        port_row.addWidget(self.port_combo, stretch=1)

        layout.addLayout(port_row)

        self.refresh_button = QPushButton("Portları &Yenile")
        self.refresh_button.clicked.connect(self._refresh_ports)
        layout.addWidget(self.refresh_button)

        self.save_button = QPushButton("&Kaydet")
        self.save_button.clicked.connect(self._on_save_clicked)
        layout.addWidget(self.save_button)

        layout.addStretch()

        self._refresh_ports()

    # -------------------------------------------------

    def set_band(self, band):

        self.band = band
        self._refresh_ports()

    # -------------------------------------------------

    def _refresh_ports(self):

        current = (
            self.port_combo.currentText()
            or (self.band.arduino_port if self.band is not None else "")
        )

        self.port_combo.blockSignals(True)

        self.port_combo.clear()
        self.port_combo.addItems(
            [p.device for p in list_ports.comports()]
        )

        self.port_combo.setCurrentText(current or "")

        self.port_combo.blockSignals(False)

    def _on_save_clicked(self):

        if self.band is None:
            return

        self.band.arduino_port = self.port_combo.currentText().strip()

        self.band_manager.save_band(self.band)

        app_logger.info(
            "[%s] Arduino portu değiştirildi: %s -> %s",
            self.operator_name, self.band.name, self.band.arduino_port
        )
