from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QLineEdit,
    QSpinBox,
    QComboBox,
    QPushButton,
    QFileDialog,
    QMessageBox
)

from modules.utils.logger import get_logger

app_logger = get_logger()

PERIOD_UNIT_LABELS = [
    ("day", "Gün"),
    ("month", "Ay"),
    ("year", "Yıl")
]


class DataRetentionSettingsPanel(QWidget):
    """
    Bir bandın veri saklama ayarını (açık/kapalı, saklama süresi
    gün/ay/yıl, arşiv klasörü) değiştirme paneli. Açıksa, saklama
    süresini aşan inceleme kayıtları silinmeden önce bir özet Excel
    raporu olarak arşiv klasörüne kaydedilir, sonra DB'den ve
    ilişkili HATA/eğitim fotoğraflarından silinir - bkz.
    DataRetentionManager, InspectionUIController._maybe_run_data_retention.
    Ayarlar penceresi içine gömülür - bkz. SettingsDialog.
    """

    def __init__(self, band_manager, band, operator_name, parent=None):

        super().__init__(parent)

        self.band_manager = band_manager
        self.band = band
        self.operator_name = operator_name

        layout = QVBoxLayout(self)

        title = QLabel("Veri Saklama")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        info_label = QLabel(
            "Açıksa, belirlediğiniz süreden eski inceleme kayıtları "
            "silinmeden önce bir özet Excel raporu olarak aşağıdaki "
            "klasöre kaydedilir - veri sessizce kaybolmaz, arşiv "
            "raporu olarak kalır. Kontrol günde bir kez yapılır."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray;")
        layout.addWidget(info_label)

        self.enabled_checkbox = QCheckBox("Veri saklama sınırını aç")
        layout.addWidget(self.enabled_checkbox)

        period_row = QHBoxLayout()
        period_row.addWidget(QLabel("En Fazla Saklama Süresi:"))

        self.period_value_spinbox = QSpinBox()
        self.period_value_spinbox.setRange(1, 999)
        period_row.addWidget(self.period_value_spinbox)

        self.period_unit_combo = QComboBox()

        for unit_key, unit_label in PERIOD_UNIT_LABELS:
            self.period_unit_combo.addItem(unit_label, unit_key)

        period_row.addWidget(self.period_unit_combo)

        period_row.addStretch()

        layout.addLayout(period_row)

        destination_row = QHBoxLayout()
        destination_row.addWidget(QLabel("Arşiv Klasörü:"))

        self.destination_input = QLineEdit()
        destination_row.addWidget(self.destination_input, stretch=1)

        self.browse_button = QPushButton("Gözat...")
        self.browse_button.clicked.connect(self._on_browse_clicked)
        destination_row.addWidget(self.browse_button)

        layout.addLayout(destination_row)

        self.save_button = QPushButton("&Kaydet")
        self.save_button.clicked.connect(self._on_save_clicked)
        layout.addWidget(self.save_button)

        layout.addStretch()

        self.set_band(band)

    # -------------------------------------------------

    def set_band(self, band):

        self.band = band

        self.enabled_checkbox.setChecked(
            band.data_retention_enabled if band is not None else False
        )
        self.period_value_spinbox.setValue(
            band.data_retention_period_value if band is not None else 1
        )

        unit = band.data_retention_period_unit if band is not None else "year"
        unit_index = self.period_unit_combo.findData(unit)
        self.period_unit_combo.setCurrentIndex(max(0, unit_index))

        self.destination_input.setText(
            band.data_retention_export_destination if band is not None else ""
        )

    # -------------------------------------------------

    def _on_browse_clicked(self):

        folder = QFileDialog.getExistingDirectory(
            self, "Arşiv Klasörü Seç", self.destination_input.text()
        )

        if folder:
            self.destination_input.setText(folder)

    # -------------------------------------------------

    def _on_save_clicked(self):

        if self.band is None:
            return

        if self.enabled_checkbox.isChecked() and not (
            self.destination_input.text().strip()
        ):

            QMessageBox.warning(
                self,
                "Uyarı",
                "Veri saklama sınırı açıksa bir arşiv klasörü seçmelisiniz."
            )

            return

        self.band.data_retention_enabled = self.enabled_checkbox.isChecked()
        self.band.data_retention_period_value = (
            self.period_value_spinbox.value()
        )
        self.band.data_retention_period_unit = (
            self.period_unit_combo.currentData()
        )
        self.band.data_retention_export_destination = (
            self.destination_input.text().strip()
        )

        self.band_manager.save_band(self.band)

        app_logger.info(
            "[%s] veri saklama ayarları değiştirildi: %s -> "
            "açık=%s, süre=%d %s, arşiv=%s",
            self.operator_name, self.band.name,
            self.band.data_retention_enabled,
            self.band.data_retention_period_value,
            self.band.data_retention_period_unit,
            self.band.data_retention_export_destination
        )
