from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QListWidget,
    QPushButton,
    QLabel
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