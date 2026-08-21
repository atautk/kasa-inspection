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
    gibi seyrek kullanılan işler MainWindow'daki "Ayarlar" penceresinde
    yaşar (bkz. main_window.py, settings_dialog.py).
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

        self.rename_button = QPushButton("Yeniden Adlandır")
        button_row.addWidget(self.rename_button)

        self.delete_button = QPushButton("Bandı Sil")
        button_row.addWidget(self.delete_button)

        layout.addLayout(button_row)
