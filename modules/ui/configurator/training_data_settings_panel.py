from PySide6.QtWidgets import (
    QWidget,
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
from modules.utils.display_terms import state_label
from modules.utils.logger import get_logger

app_logger = get_logger()


class TrainingDataSettingsPanel(QWidget):
    """
    Bir bandın model eğitimi veri toplama ayarını (açık/kapalı)
    değiştirme ve o ana kadar ne kadar veri biriktiğini gösteren
    panel. Açıksa, her onaylı log olayında göz bazında referans/
    canlı kırpma görüntü çiftleri "training_data/" altında DOLU/BOŞ
    klasörlenerek diske kaydedilir - bkz. TrainingDataManager. Ayarlar
    penceresi içine gömülür - bkz. SettingsDialog.
    """

    TABLE_COLUMNS = ["Göz", "Durum", "Örnek Sayısı", "Gözden Geçirilmeli", "Yeterlilik"]

    def __init__(self, band_manager, band, operator_name, parent=None):

        super().__init__(parent)

        self.band_manager = band_manager
        self.band = band
        self.operator_name = operator_name
        self.training_data_manager = TrainingDataManager()

        layout = QVBoxLayout(self)

        title = QLabel("Model Eğitimi Veri Toplama")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        info_label = QLabel(
            "Açıksa, her onaylı inceleme sonucunda gözlerin referans/"
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
        self.enabled_checkbox.stateChanged.connect(self._on_toggled)
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

        self._loading = False

        self.set_band(band)

    # -------------------------------------------------

    def set_band(self, band):

        self.band = band

        self._loading = True
        self.enabled_checkbox.setChecked(
            band.training_data_collection_enabled if band is not None else False
        )
        self._loading = False

        self._reload_summary()

    def _on_toggled(self):

        if self._loading or self.band is None:
            return

        self.band.training_data_collection_enabled = (
            self.enabled_checkbox.isChecked()
        )

        self.band_manager.save_band(self.band)

        app_logger.info(
            "[%s] model eğitimi veri toplama %s: %s",
            self.operator_name,
            "açıldı" if self.band.training_data_collection_enabled else "kapatıldı",
            self.band.name
        )

    # -------------------------------------------------
    # Toplanan Veri Özeti
    # -------------------------------------------------

    def _reload_summary(self):

        if self.band is None:
            self._fill_table([])
            self.summary_label.setText("-")
            return

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
                    state_label(state),
                    data["count"],
                    data["flagged"],
                    self.training_data_manager.assess_sufficiency(
                        bottleneck_count
                    )
                ))

        self._fill_table(rows)

        roi_count = len(summary)

        self.summary_label.setText(
            f"{roi_count} göz, toplam {total_samples} örnek"
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
