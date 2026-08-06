from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QPushButton
)

from ..window_utils import restore_or_center, save_geometry

SETTINGS_KEY = "training_data_settings_dialog"


class TrainingDataSettingsDialog(QDialog):
    """
    Bir bandın model eğitimi veri toplama ayarını (açık/kapalı)
    değiştirme penceresi. Açıksa, her onaylı log olayında ROI bazında
    referans/canlı kırpma görüntü çiftleri "training_data/" altında
    DOLU/BOŞ klasörlenerek diske kaydedilir - bkz. TrainingDataManager.
    """

    def __init__(self, band, parent=None):

        super().__init__(parent)

        self.setWindowTitle(f"Model Eğitimi Veri Toplama - {band.name}")
        self.setModal(True)
        restore_or_center(self, SETTINGS_KEY, 460, 180)

        layout = QVBoxLayout(self)

        info_label = QLabel(
            "Açıksa, her onaylı inceleme sonucunda ROI'lerin referans/"
            "canlı görüntü çiftleri diske kaydedilir (DOLU/BOŞ olarak "
            "klasörlenir). Amaç: ileride bir görüntü sınıflandırma "
            "modeli eğitmek için veri biriktirmek. Kapalıyken hiçbir "
            "ek dosya yazılmaz."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray;")
        layout.addWidget(info_label)

        self.enabled_checkbox = QCheckBox(
            "Bu bant için eğitim verisi topla"
        )
        self.enabled_checkbox.setChecked(
            band.training_data_collection_enabled
        )
        layout.addWidget(self.enabled_checkbox)

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

    def is_enabled(self) -> bool:

        return self.enabled_checkbox.isChecked()
