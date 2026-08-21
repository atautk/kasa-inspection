from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QPushButton,
    QFileDialog,
    QMessageBox
)

from modules.utils.logger import get_logger

app_logger = get_logger()


class AutoBackupSettingsPanel(QWidget):
    """
    Bir bandın otomatik yedekleme ayarını (açık/kapalı, hedef klasör,
    sıklık, saklanacak yedek sayısı) değiştirme paneli. Açıksa,
    inspection_log.db + ng_captures/ periyodik olarak hedef klasöre
    kopyalanır ve eski yedekler otomatik temizlenir - bkz.
    BackupManager, InspectionUIController._maybe_run_auto_backup.
    Ayarlar penceresi içine gömülür - bkz. SettingsDialog.
    """

    def __init__(self, band_manager, band, operator_name, parent=None):

        super().__init__(parent)

        self.band_manager = band_manager
        self.band = band
        self.operator_name = operator_name

        layout = QVBoxLayout(self)

        title = QLabel("Otomatik Yedekleme")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        info_label = QLabel(
            "Açıksa, inceleme geçmişi (SQLite log + hata fotoğrafları) "
            "periyodik olarak aşağıdaki klasöre kopyalanır. Mümkünse "
            "bu klasörün band'in bulunduğu diskten FARKLI bir yerde "
            "(ayrı disk, ağ paylaşımı) olması önerilir - aynı diskte "
            "yedeklemek disk arızasına karşı koruma sağlamaz."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray;")
        layout.addWidget(info_label)

        self.enabled_checkbox = QCheckBox("Otomatik yedeklemeyi aç")
        layout.addWidget(self.enabled_checkbox)

        destination_row = QHBoxLayout()
        destination_row.addWidget(QLabel("Hedef Klasör:"))

        self.destination_input = QLineEdit()
        destination_row.addWidget(self.destination_input, stretch=1)

        self.browse_button = QPushButton("Gözat...")
        self.browse_button.clicked.connect(self._on_browse_clicked)
        destination_row.addWidget(self.browse_button)

        layout.addLayout(destination_row)

        interval_row = QHBoxLayout()
        interval_row.addWidget(QLabel("Yedekleme Sıklığı (saat):"))

        self.interval_spinbox = QDoubleSpinBox()
        self.interval_spinbox.setRange(1.0, 720.0)
        self.interval_spinbox.setSingleStep(1.0)
        interval_row.addWidget(self.interval_spinbox, stretch=1)

        layout.addLayout(interval_row)

        keep_row = QHBoxLayout()
        keep_row.addWidget(QLabel("Saklanacak Yedek Sayısı (0 = sınırsız):"))

        self.keep_count_spinbox = QSpinBox()
        self.keep_count_spinbox.setRange(0, 1000)
        keep_row.addWidget(self.keep_count_spinbox, stretch=1)

        layout.addLayout(keep_row)

        self.save_button = QPushButton("&Kaydet")
        self.save_button.clicked.connect(self._on_save_clicked)
        layout.addWidget(self.save_button)

        layout.addStretch()

        self.set_band(band)

    # -------------------------------------------------

    def set_band(self, band):

        self.band = band

        self.enabled_checkbox.setChecked(
            band.auto_backup_enabled if band is not None else False
        )
        self.destination_input.setText(
            band.auto_backup_destination if band is not None else ""
        )
        self.interval_spinbox.setValue(
            band.auto_backup_interval_hours if band is not None else 24.0
        )
        self.keep_count_spinbox.setValue(
            band.auto_backup_keep_count if band is not None else 30
        )

    # -------------------------------------------------

    def _on_browse_clicked(self):

        folder = QFileDialog.getExistingDirectory(
            self, "Yedekleme Klasörü Seç", self.destination_input.text()
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
                "Otomatik yedekleme açıksa bir hedef klasör seçmelisiniz."
            )

            return

        self.band.auto_backup_enabled = self.enabled_checkbox.isChecked()
        self.band.auto_backup_destination = (
            self.destination_input.text().strip()
        )
        self.band.auto_backup_interval_hours = self.interval_spinbox.value()
        self.band.auto_backup_keep_count = self.keep_count_spinbox.value()

        self.band_manager.save_band(self.band)

        app_logger.info(
            "[%s] otomatik yedekleme ayarları değiştirildi: %s -> "
            "açık=%s, hedef=%s, sıklık=%.1f saat, sakla=%d",
            self.operator_name, self.band.name,
            self.band.auto_backup_enabled,
            self.band.auto_backup_destination,
            self.band.auto_backup_interval_hours,
            self.band.auto_backup_keep_count
        )
