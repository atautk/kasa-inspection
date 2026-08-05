import numpy as np

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QSizePolicy,
    QComboBox
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
        set_channels(items: list[tuple[str, str | None]])
        get_selected_channel_id() -> str | None

    Controller'ın dinlediği sinyaller (butonlar):

        camera_button.clicked
        capture_button.clicked
        retake_button.clicked
        channel_combo.currentIndexChanged
    """

    def __init__(self):

        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # ---------- Kamera Kanalı Seçimi ----------
        # (Aynı kasayı farklı açılardan izleyen ek kameralar varsa,
        # hangisi için fotoğraf çekildiğini seçmeye yarar. Bandın tek
        # kamerası varsa bu satır tamamen gizlenir - bkz. set_channels().)

        self.channel_container = QWidget()

        channel_row = QHBoxLayout(self.channel_container)
        channel_row.setContentsMargins(0, 0, 0, 0)

        channel_row.addWidget(QLabel("Fotoğrafı Çekilecek Kamera:"))

        self.channel_combo = QComboBox()
        self.channel_combo.setToolTip(
            "Bu band birden fazla kameraya sahip. Hangi kameranın "
            "referans fotoğrafını düzenlediğinizi buradan seçin."
        )
        channel_row.addWidget(self.channel_combo, stretch=1)

        layout.addWidget(self.channel_container)

        self.channel_container.setVisible(False)

        # ---------- Preview ----------

        self._last_frame = None

        self.preview_label = QLabel("Kamera kapalı")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFrameShape(QFrame.Box)
        self.preview_label.setMinimumSize(320, 240)
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

        self._last_frame = frame

        self._render_preview(frame)

    def _render_preview(self, frame: np.ndarray):

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

        self._last_frame = None

        self.preview_label.clear()
        self.preview_label.setText("Kamera kapalı")

    # -------------------------------------------------
    # Pencere Yeniden Boyutlanınca
    # -------------------------------------------------

    def resizeEvent(self, event):

        super().resizeEvent(event)

        if self._last_frame is not None:
            self._render_preview(self._last_frame)

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

    # -------------------------------------------------
    # Kamera Kanalı Seçimi
    # -------------------------------------------------

    def set_channels(self, items: list):
        """
        items: [(etiket, channel_id_ya_da_None), ...]
        İlk eleman her zaman birincil kamerayı (channel_id=None)
        temsil etmeli. Sadece birincil varsa (tek eleman), seçim
        kutusu tek kameralı bandlarda kafa karıştırmasın diye
        tamamen gizlenir.
        """

        self.channel_combo.blockSignals(True)

        self.channel_combo.clear()

        for label, channel_id in items:
            self.channel_combo.addItem(label, channel_id)

        self.channel_combo.blockSignals(False)

        self.channel_container.setVisible(len(items) > 1)

    def get_selected_channel_id(self):

        return self.channel_combo.currentData()