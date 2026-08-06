from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QPushButton
)

from ..window_utils import restore_or_center, save_geometry

SETTINGS_KEY = "reference_reminder_dialog"


class ReferenceReminderDialog(QDialog):
    """
    Bir bandın referans fotoğrafı yaşlanma hatırlatıcısını ayarlama
    penceresi. Işık/kamera koşulları zamanla kayabileceğinden,
    referans fotoğrafı çok eskiyse (dosyanın son değiştirilme
    tarihinden bu yana) hatırlatma yapılır. 0 gün = kapalı.
    """

    def __init__(self, band, parent=None):

        super().__init__(parent)

        self.setWindowTitle(f"Referans Yenileme Hatırlatıcısı - {band.name}")
        self.setModal(True)
        restore_or_center(self, SETTINGS_KEY, 420, 160)

        layout = QVBoxLayout(self)

        info_label = QLabel(
            "Işık/kamera koşulları zamanla kayabilir. Referans "
            "fotoğrafı (ve varsa ek kamera kanallarının referansları) "
            "burada girilen gün sayısından daha eskiyse hatırlatma "
            "yapılır. 0 gün = kapalı."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray;")
        layout.addWidget(info_label)

        row = QHBoxLayout()
        row.addWidget(QLabel("Hatırlatma Süresi (gün):"))
        self.days_spinbox = QSpinBox()
        self.days_spinbox.setRange(0, 3650)
        self.days_spinbox.setValue(band.reference_max_age_days)
        row.addWidget(self.days_spinbox, stretch=1)
        layout.addLayout(row)

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

    def get_max_age_days(self) -> int:

        return self.days_spinbox.value()
