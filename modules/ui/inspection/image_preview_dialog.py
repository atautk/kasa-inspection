import cv2

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QScrollArea,
    QLabel
)
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt

from ..window_utils import restore_or_center, save_geometry

SETTINGS_KEY = "image_preview"


class ImagePreviewDialog(QDialog):

    def __init__(self, image_path, title="Fotoğraf", parent=None):

        super().__init__(parent)

        self.setWindowTitle(title)
        restore_or_center(self, SETTINGS_KEY, 1100, 850)

        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet(
            "background-color: black;"
        )
        scroll.setWidget(self.image_label)

        self._load_image(image_path)

    # -------------------------------------------------

    def closeEvent(self, event):

        save_geometry(self, SETTINGS_KEY)

        super().closeEvent(event)

    # -------------------------------------------------

    def _load_image(self, image_path):

        image = cv2.imread(image_path)

        if image is None:

            self.image_label.setText("Fotoğraf okunamadı")
            self.image_label.setStyleSheet(
                "background-color: black; color: white;"
            )
            return

        height, width = image.shape[:2]

        rgb = image[:, :, ::-1].copy()

        qimage = QImage(
            rgb.data,
            width,
            height,
            rgb.strides[0],
            QImage.Format_RGB888
        ).copy()

        # .copy() ZORUNLU: kopyalanmazsa QImage rgb'nin arabelleğini
        # sarmalar, bu fonksiyon dönünce rgb serbest kalabilir ve
        # ilk (gecikmeli/async) paint sırasında Qt geçersiz belleğe
        # erişip "access violation" ile çöker.

        pixmap = QPixmap.fromImage(qimage)

        self.image_label.setPixmap(pixmap)
        self.image_label.resize(pixmap.size())
