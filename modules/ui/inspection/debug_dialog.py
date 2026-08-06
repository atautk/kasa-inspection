import cv2
import numpy as np

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QDoubleSpinBox,
    QSpinBox,
    QScrollArea
)
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt

from ..window_utils import restore_or_center, save_geometry

SETTINGS_KEY = "debug_dialog"


class DebugDialog(QDialog):
    """
    ROI bazında referans/güncel/fark/binary karelerini, değişim
    eşiğini ve onay karesi sayısını bir arada gösteren pencere. Bu
    ayarlar burada değiştirildiğinde canlı olarak inceleme motoruna
    uygulanır (Debug açıkken izleyerek ayarlamak için).
    """

    THUMB_WIDTH = 220
    THUMB_HEIGHT = 160
    TITLE_HEIGHT = 20

    LABELS = [
        ("reference", "Reference"),
        ("current", "Current"),
        ("difference", "Difference"),
        ("binary", "Binary")
    ]

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setWindowTitle("Debug")
        restore_or_center(self, SETTINGS_KEY, 900, 650)

        layout = QVBoxLayout(self)

        threshold_row = QHBoxLayout()

        threshold_row.addWidget(QLabel("Değişim Eşiği (%):"))

        self.threshold_spinbox = QDoubleSpinBox()
        self.threshold_spinbox.setRange(0.0, 100.0)
        self.threshold_spinbox.setDecimals(1)
        self.threshold_spinbox.setSingleStep(0.1)
        threshold_row.addWidget(self.threshold_spinbox)

        threshold_row.addStretch()

        layout.addLayout(threshold_row)

        confirm_row = QHBoxLayout()

        confirm_row.addWidget(
            QLabel(
                "Onay Karesi Sayısı (kamera titremesi filtresi):"
            )
        )

        self.confirm_frames_spinbox = QSpinBox()
        self.confirm_frames_spinbox.setRange(1, 30)
        confirm_row.addWidget(self.confirm_frames_spinbox)

        confirm_row.addStretch()

        layout.addLayout(confirm_row)

        blur_row = QHBoxLayout()

        blur_row.addWidget(QLabel("Bulanıklık Eşiği (Laplacian varyansı):"))

        self.blur_threshold_spinbox = QDoubleSpinBox()
        self.blur_threshold_spinbox.setRange(0.0, 10000.0)
        self.blur_threshold_spinbox.setDecimals(1)
        self.blur_threshold_spinbox.setSingleStep(10.0)
        blur_row.addWidget(self.blur_threshold_spinbox)

        self.sharpness_label = QLabel("Anlık netlik: -")
        blur_row.addWidget(self.sharpness_label)

        blur_row.addStretch()

        layout.addLayout(blur_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        self.image_label = QLabel("Veri yok")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet(
            "background-color: black; color: white;"
        )
        scroll.setWidget(self.image_label)

    # -------------------------------------------------
    # Eşik Ayarı
    # -------------------------------------------------

    def set_threshold(self, value: float):

        self.threshold_spinbox.blockSignals(True)
        self.threshold_spinbox.setValue(value)
        self.threshold_spinbox.blockSignals(False)

    def get_threshold(self) -> float:

        return self.threshold_spinbox.value()

    # -------------------------------------------------
    # Onay Karesi Sayısı Ayarı
    # -------------------------------------------------

    def set_confirm_frames(self, value: int):

        self.confirm_frames_spinbox.blockSignals(True)
        self.confirm_frames_spinbox.setValue(value)
        self.confirm_frames_spinbox.blockSignals(False)

    def get_confirm_frames(self) -> int:

        return self.confirm_frames_spinbox.value()

    # -------------------------------------------------
    # Bulanıklık Eşiği Ayarı
    # -------------------------------------------------

    def set_blur_threshold(self, value: float):

        self.blur_threshold_spinbox.blockSignals(True)
        self.blur_threshold_spinbox.setValue(value)
        self.blur_threshold_spinbox.blockSignals(False)

    def get_blur_threshold(self) -> float:

        return self.blur_threshold_spinbox.value()

    def set_current_sharpness(self, value: float):

        self.sharpness_label.setText(f"Anlık netlik: {value:.1f}")

    # -------------------------------------------------

    def closeEvent(self, event):

        save_geometry(self, SETTINGS_KEY)

        super().closeEvent(event)

    # -------------------------------------------------
    # Debug Görüntülerini Göster
    # -------------------------------------------------

    def show_debug(self, debug: dict):

        if not debug:

            self.image_label.clear()
            self.image_label.setText("Veri yok")

            return

        rois = sorted(debug.keys())

        canvas = np.zeros(
            (
                self.THUMB_HEIGHT * len(rois),
                self.THUMB_WIDTH * len(self.LABELS),
                3
            ),
            dtype=np.uint8
        )

        for row, roi_name in enumerate(rois):

            compare = debug[roi_name]

            for col, (key, label) in enumerate(self.LABELS):

                thumb = self._build_thumbnail(
                    compare.get(key),
                    f"{roi_name} - {label}"
                )

                y = row * self.THUMB_HEIGHT
                x = col * self.THUMB_WIDTH

                canvas[
                    y:y + self.THUMB_HEIGHT,
                    x:x + self.THUMB_WIDTH
                ] = thumb

        height, width = canvas.shape[:2]

        rgb = canvas[:, :, ::-1].copy()

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

        self.image_label.setPixmap(QPixmap.fromImage(qimage))
        self.image_label.resize(width, height)

    # -------------------------------------------------
    # Küçük Resim Oluştur
    # -------------------------------------------------

    def _build_thumbnail(self, image, title):

        thumb = np.zeros(
            (self.THUMB_HEIGHT, self.THUMB_WIDTH, 3),
            dtype=np.uint8
        )

        if image is not None:

            if len(image.shape) == 2:
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

            resized = cv2.resize(
                image,
                (self.THUMB_WIDTH, self.THUMB_HEIGHT - self.TITLE_HEIGHT)
            )

            thumb[self.TITLE_HEIGHT:, :] = resized

        cv2.rectangle(
            thumb,
            (0, 0),
            (self.THUMB_WIDTH, self.TITLE_HEIGHT),
            (40, 40, 40),
            -1
        )

        cv2.putText(
            thumb,
            title,
            (4, self.TITLE_HEIGHT - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (255, 255, 255),
            1
        )

        cv2.rectangle(
            thumb,
            (0, 0),
            (self.THUMB_WIDTH - 1, self.THUMB_HEIGHT - 1),
            (90, 90, 90),
            1
        )

        return thumb
