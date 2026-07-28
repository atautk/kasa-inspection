import numpy as np

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QSizePolicy
)
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt


class ReferencePage(QWidget):
    """
    Reference sekmesi.

    Bu sınıf SADECE UI'dan sorumludur.
    Kamera, OpenCV veya ArUco hakkında hiçbir şey bilmez.

    Controller (ConfiguratorController), aşağıdaki public
    metodları çağırarak bu sayfayı günceller:

        set_preview(frame)
        clear_preview()
        set_status(text)
        set_marker_status(text)
        set_resolution(width, height)
        enable_capture(enabled: bool)
        enable_camera_button(enabled: bool)
        enable_retake_button(enabled: bool)

    Controller'ın dinlediği sinyaller (butonlar):

        camera_button.clicked
        capture_button.clicked
        retake_button.clicked
    """

    def __init__(self):

        super().__init__()

        layout = QVBoxLayout(self)

        # ---------- Preview ----------

        self.preview_label = QLabel("Kamera kapalı")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFrameShape(QFrame.Box)
        self.preview_label.setMinimumSize(640, 480)
        self.preview_label.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        self.preview_label.setStyleSheet(
            "background-color: black; color: white;"
        )
        layout.addWidget(self.preview_label)

        # ---------- Bilgi Satırları ----------

        self.status_label = QLabel("Durum: -")
        layout.addWidget(self.status_label)

        self.marker_label = QLabel("Marker: -")
        layout.addWidget(self.marker_label)

        self.resolution_label = QLabel("Çözünürlük: -")
        layout.addWidget(self.resolution_label)

        # ---------- Butonlar ----------

        button_row = QHBoxLayout()

        self.camera_button = QPushButton("Kamera Aç")
        button_row.addWidget(self.camera_button)

        self.capture_button = QPushButton("Fotoğraf Çek")
        self.capture_button.setEnabled(False)
        button_row.addWidget(self.capture_button)

        self.retake_button = QPushButton("Yeniden Çek")
        self.retake_button.setEnabled(False)
        button_row.addWidget(self.retake_button)

        layout.addLayout(button_row)

    # -------------------------------------------------
    # Preview Güncelleme
    # -------------------------------------------------

    def set_preview(self, frame: np.ndarray):

        if frame is None:
            return

        height, width = frame.shape[:2]

        # frame BGR (OpenCV formatı) olarak varsayılır.
        # UI katmanı bunu sadece gösterim için RGB'ye çevirir,
        # bu bir görüntü işleme algoritması değildir.

        rgb = frame[:, :, ::-1].copy()

        image = QImage(
            rgb.data,
            width,
            height,
            rgb.strides[0],
            QImage.Format_RGB888
        )

        pixmap = QPixmap.fromImage(image).scaled(
            self.preview_label.width(),
            self.preview_label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.preview_label.setPixmap(pixmap)

        self.set_resolution(width, height)

    def clear_preview(self):

        self.preview_label.clear()
        self.preview_label.setText("Kamera kapalı")

    # -------------------------------------------------
    # Bilgi Güncelleme
    # -------------------------------------------------

    def set_status(self, text: str):

        self.status_label.setText(f"Durum: {text}")

    def set_marker_status(self, text: str):

        self.marker_label.setText(f"Marker: {text}")

    def set_resolution(self, width: int, height: int):

        self.resolution_label.setText(
            f"Çözünürlük: {width} x {height}"
        )

    # -------------------------------------------------
    # Buton Durumları
    # -------------------------------------------------

    def enable_capture(self, enabled: bool):

        self.capture_button.setEnabled(enabled)

    def enable_camera_button(self, enabled: bool):

        self.camera_button.setEnabled(enabled)

    def enable_retake_button(self, enabled: bool):

        self.retake_button.setEnabled(enabled)