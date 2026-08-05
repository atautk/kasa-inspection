from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QLabel
)


class BandPage(QWidget):
    """
    Günlük kullanımda ihtiyaç duyulan tek şey band seçip açmaktır -
    bu sayfa bilerek sade tutulur. Doğrulama, dışa/içe aktarma,
    operatör/log yönetimi, Telegram ve kamera kanalı/Arduino ayarları
    gibi seyrek kullanılan işler MainWindow'daki "Yönetim" menüsünden
    açılan pencerelerde yaşar (bkz. main_window.py, camera_channels_
    dialog.py, arduino_settings_dialog.py).
    """

    def __init__(self):

        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Bandlar")
        layout.addWidget(title)

        self.band_list = QListWidget()
        layout.addWidget(self.band_list)

        button_row = QHBoxLayout()

        self.new_button = QPushButton("Yeni Band")
        button_row.addWidget(self.new_button)

        self.open_button = QPushButton("Bandı Aç")
        button_row.addWidget(self.open_button)

        layout.addLayout(button_row)
