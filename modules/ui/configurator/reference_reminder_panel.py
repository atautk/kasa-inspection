from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QPushButton
)

from modules.utils.logger import get_logger

app_logger = get_logger()


class ReferenceReminderPanel(QWidget):
    """
    Bir bandın referans fotoğrafı yaşlanma hatırlatıcısını ayarlama
    paneli. Işık/kamera koşulları zamanla kayabileceğinden, referans
    fotoğrafı çok eskiyse (dosyanın son değiştirilme tarihinden bu
    yana) hatırlatma yapılır. 0 gün = kapalı. Ayarlar penceresi
    içine gömülür - bkz. SettingsDialog.
    """

    def __init__(self, band_manager, band, operator_name, parent=None):

        super().__init__(parent)

        self.band_manager = band_manager
        self.band = band
        self.operator_name = operator_name

        layout = QVBoxLayout(self)

        title = QLabel("Referans Yenileme Hatırlatıcısı")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

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
        row.addWidget(self.days_spinbox, stretch=1)
        layout.addLayout(row)

        self.save_button = QPushButton("&Kaydet")
        self.save_button.clicked.connect(self._on_save_clicked)
        layout.addWidget(self.save_button)

        layout.addStretch()

        self._load_from_band()

    # -------------------------------------------------

    def set_band(self, band):

        self.band = band
        self._load_from_band()

    def _load_from_band(self):

        self.days_spinbox.setValue(
            self.band.reference_max_age_days if self.band is not None else 0
        )

    def _on_save_clicked(self):

        if self.band is None:
            return

        self.band.reference_max_age_days = self.days_spinbox.value()

        self.band_manager.save_band(self.band)

        app_logger.info(
            "[%s] referans yenileme hatırlatıcısı değiştirildi: %s -> "
            "%d gün",
            self.operator_name, self.band.name,
            self.band.reference_max_age_days
        )
