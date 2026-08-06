from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QDoubleSpinBox,
    QPushButton
)

from ..window_utils import restore_or_center, save_geometry

SETTINGS_KEY = "shift_settings_dialog"


class ShiftSettingsDialog(QDialog):
    """
    Bir bandın vardiya bazlı üretim hedefini ayarlama penceresi.
    Hedef 0 ise vardiya takibi/uyarısı tamamen kapalı demektir - bkz.
    InspectionUIController._maybe_check_shift_progress.
    """

    def __init__(self, band, parent=None):

        super().__init__(parent)

        self.setWindowTitle(f"Vardiya Ayarları - {band.name}")
        self.setModal(True)
        restore_or_center(self, SETTINGS_KEY, 420, 180)

        layout = QVBoxLayout(self)

        info_label = QLabel(
            "Vardiya hedefi 0 olarak bırakılırsa üretim takibi ve "
            "gerisinde kalma uyarısı kapalı olur."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray;")
        layout.addWidget(info_label)

        target_row = QHBoxLayout()
        target_row.addWidget(QLabel("Vardiya Hedefi (kasa sayısı):"))
        self.target_spinbox = QSpinBox()
        self.target_spinbox.setRange(0, 1_000_000)
        self.target_spinbox.setValue(band.shift_target_count)
        target_row.addWidget(self.target_spinbox, stretch=1)
        layout.addLayout(target_row)

        duration_row = QHBoxLayout()
        duration_row.addWidget(QLabel("Vardiya Süresi (saat):"))
        self.duration_spinbox = QDoubleSpinBox()
        self.duration_spinbox.setRange(0.5, 24.0)
        self.duration_spinbox.setSingleStep(0.5)
        self.duration_spinbox.setValue(band.shift_duration_hours)
        duration_row.addWidget(self.duration_spinbox, stretch=1)
        layout.addLayout(duration_row)

        button_row = QHBoxLayout()

        button_row.addStretch()

        self.cancel_button = QPushButton("İptal")
        self.cancel_button.clicked.connect(self.reject)
        button_row.addWidget(self.cancel_button)

        self.save_button = QPushButton("&Kaydet")
        self.save_button.clicked.connect(self.accept)
        button_row.addWidget(self.save_button)

        layout.addLayout(button_row)

    # -------------------------------------------------

    def closeEvent(self, event):

        save_geometry(self, SETTINGS_KEY)

        super().closeEvent(event)

    # -------------------------------------------------

    def get_target_count(self) -> int:

        return self.target_spinbox.value()

    def get_duration_hours(self) -> float:

        return self.duration_spinbox.value()
