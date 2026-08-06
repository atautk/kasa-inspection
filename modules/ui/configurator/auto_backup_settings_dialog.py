from PySide6.QtWidgets import (
    QDialog,
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

from ..window_utils import restore_or_center, save_geometry

SETTINGS_KEY = "auto_backup_settings_dialog"


class AutoBackupSettingsDialog(QDialog):
    """
    Bir bandın otomatik yedekleme ayarını (açık/kapalı, hedef klasör,
    sıklık, saklanacak yedek sayısı) değiştirme penceresi. Açıksa,
    inspection_log.db + ng_captures/ periyodik olarak hedef klasöre
    kopyalanır ve eski yedekler otomatik temizlenir - bkz.
    BackupManager, InspectionUIController._maybe_run_auto_backup.
    """

    def __init__(self, band, parent=None):

        super().__init__(parent)

        self.setWindowTitle(f"Otomatik Yedekleme - {band.name}")
        self.setModal(True)
        restore_or_center(self, SETTINGS_KEY, 480, 240)

        layout = QVBoxLayout(self)

        info_label = QLabel(
            "Açıksa, inspection geçmişi (SQLite log + NG fotoğrafları) "
            "periyodik olarak aşağıdaki klasöre kopyalanır. Mümkünse "
            "bu klasörün band'in bulunduğu diskten FARKLI bir yerde "
            "(ayrı disk, ağ paylaşımı) olması önerilir - aynı diskte "
            "yedeklemek disk arızasına karşı koruma sağlamaz."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray;")
        layout.addWidget(info_label)

        self.enabled_checkbox = QCheckBox("Otomatik yedeklemeyi aç")
        self.enabled_checkbox.setChecked(band.auto_backup_enabled)
        layout.addWidget(self.enabled_checkbox)

        destination_row = QHBoxLayout()
        destination_row.addWidget(QLabel("Hedef Klasör:"))

        self.destination_input = QLineEdit()
        self.destination_input.setText(band.auto_backup_destination)
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
        self.interval_spinbox.setValue(band.auto_backup_interval_hours)
        interval_row.addWidget(self.interval_spinbox, stretch=1)

        layout.addLayout(interval_row)

        keep_row = QHBoxLayout()
        keep_row.addWidget(QLabel("Saklanacak Yedek Sayısı (0 = sınırsız):"))

        self.keep_count_spinbox = QSpinBox()
        self.keep_count_spinbox.setRange(0, 1000)
        self.keep_count_spinbox.setValue(band.auto_backup_keep_count)
        keep_row.addWidget(self.keep_count_spinbox, stretch=1)

        layout.addLayout(keep_row)

        button_row = QHBoxLayout()

        button_row.addStretch()

        self.cancel_button = QPushButton("İptal")
        self.cancel_button.clicked.connect(self.reject)
        button_row.addWidget(self.cancel_button)

        self.save_button = QPushButton("&Kaydet")
        self.save_button.clicked.connect(self._on_save_clicked)
        button_row.addWidget(self.save_button)

        layout.addLayout(button_row)

    # -------------------------------------------------

    def closeEvent(self, event):

        save_geometry(self, SETTINGS_KEY)

        super().closeEvent(event)

    # -------------------------------------------------

    def _on_browse_clicked(self):

        folder = QFileDialog.getExistingDirectory(
            self, "Yedekleme Klasörü Seç", self.destination_input.text()
        )

        if folder:
            self.destination_input.setText(folder)

    # -------------------------------------------------

    def _on_save_clicked(self):

        if self.enabled_checkbox.isChecked() and not (
            self.destination_input.text().strip()
        ):

            QMessageBox.warning(
                self,
                "Uyarı",
                "Otomatik yedekleme açıksa bir hedef klasör seçmelisiniz."
            )

            return

        self.accept()

    # -------------------------------------------------

    def is_enabled(self) -> bool:

        return self.enabled_checkbox.isChecked()

    def get_destination(self) -> str:

        return self.destination_input.text().strip()

    def get_interval_hours(self) -> float:

        return self.interval_spinbox.value()

    def get_keep_count(self) -> int:

        return self.keep_count_spinbox.value()
