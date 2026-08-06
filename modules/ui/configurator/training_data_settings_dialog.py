from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView
)

from modules.configuration.training_data_manager import TrainingDataManager

from ..window_utils import restore_or_center, save_geometry

SETTINGS_KEY = "training_data_settings_dialog"


class TrainingDataSettingsDialog(QDialog):
    """
    Bir bandın model eğitimi veri toplama ayarını (açık/kapalı)
    değiştirme ve o ana kadar ne kadar veri biriktiğini gösteren
    pencere. Açıksa, her onaylı log olayında ROI bazında referans/
    canlı kırpma görüntü çiftleri "training_data/" altında DOLU/BOŞ
    klasörlenerek diske kaydedilir - bkz. TrainingDataManager.
    """

    TABLE_COLUMNS = ["ROI", "Durum", "Örnek Sayısı", "Gözden Geçirilmeli", "Yeterlilik"]

    def __init__(self, band, parent=None):

        super().__init__(parent)

        self.band = band
        self.training_data_manager = TrainingDataManager()

        self.setWindowTitle(f"Model Eğitimi Veri Toplama - {band.name}")
        self.setModal(True)
        restore_or_center(self, SETTINGS_KEY, 620, 460)

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

        # ---------- Toplanan Veri Özeti ----------

        summary_row = QHBoxLayout()

        summary_row.addWidget(QLabel("Toplanan Veri:"))

        self.summary_label = QLabel("-")
        summary_row.addWidget(self.summary_label, stretch=1)

        self.refresh_button = QPushButton("Yenile")
        self.refresh_button.clicked.connect(self._reload_summary)
        summary_row.addWidget(self.refresh_button)

        layout.addLayout(summary_row)

        self.sufficiency_note_label = QLabel(
            "Not: \"Yeterlilik\" küçük/kontrollü bir ikili sınıflandırma "
            "görevi için kaba bir gösterge, kesin bir bilimsel eşik "
            "değil - gerçek ihtiyaç görüntü çeşitliliğine göre değişir."
        )
        self.sufficiency_note_label.setWordWrap(True)
        self.sufficiency_note_label.setStyleSheet(
            "color: gray; font-style: italic;"
        )
        layout.addWidget(self.sufficiency_note_label)

        self.summary_table = QTableWidget()
        self.summary_table.setColumnCount(len(self.TABLE_COLUMNS))
        self.summary_table.setHorizontalHeaderLabels(self.TABLE_COLUMNS)
        self.summary_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        self.summary_table.verticalHeader().setVisible(False)
        self.summary_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.summary_table, stretch=1)

        # ---------- Butonlar ----------

        button_row = QHBoxLayout()

        button_row.addStretch()

        self.cancel_button = QPushButton("İptal")
        self.cancel_button.clicked.connect(self.reject)
        button_row.addWidget(self.cancel_button)

        self.save_button = QPushButton("&Kaydet")
        self.save_button.clicked.connect(self.accept)
        button_row.addWidget(self.save_button)

        layout.addLayout(button_row)

        self._reload_summary()

    # -------------------------------------------------

    def closeEvent(self, event):

        save_geometry(self, SETTINGS_KEY)

        super().closeEvent(event)

    # -------------------------------------------------

    def is_enabled(self) -> bool:

        return self.enabled_checkbox.isChecked()

    # -------------------------------------------------
    # Toplanan Veri Özeti
    # -------------------------------------------------

    def _reload_summary(self):

        summary = self.training_data_manager.compute_summary(self.band)

        total_samples = 0
        total_flagged = 0

        rows = []

        for roi_name in sorted(summary.keys()):

            state_counts = summary[roi_name]

            bottleneck_count = min(
                (data["count"] for data in state_counts.values()),
                default=0
            )

            for state in sorted(state_counts.keys()):

                data = state_counts[state]

                total_samples += data["count"]
                total_flagged += data["flagged"]

                rows.append((
                    roi_name,
                    state,
                    data["count"],
                    data["flagged"],
                    self.training_data_manager.assess_sufficiency(
                        bottleneck_count
                    )
                ))

        self._fill_table(rows)

        roi_count = len(summary)

        self.summary_label.setText(
            f"{roi_count} ROI, toplam {total_samples} örnek"
            + (
                f" ({total_flagged} gözden geçirilmeli)"
                if total_flagged else ""
            )
        )

    def _fill_table(self, rows: list):

        self.summary_table.setRowCount(len(rows))

        for row_index, (roi_name, state, count, flagged, sufficiency) in (
            enumerate(rows)
        ):

            self.summary_table.setItem(
                row_index, 0, QTableWidgetItem(roi_name)
            )
            self.summary_table.setItem(
                row_index, 1, QTableWidgetItem(state)
            )
            self.summary_table.setItem(
                row_index, 2, QTableWidgetItem(str(count))
            )
            self.summary_table.setItem(
                row_index, 3,
                QTableWidgetItem(str(flagged) if flagged else "-")
            )
            self.summary_table.setItem(
                row_index, 4, QTableWidgetItem(sufficiency)
            )
