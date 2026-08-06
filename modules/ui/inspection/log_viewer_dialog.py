import json
from datetime import datetime

import cv2

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QTabWidget,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLabel,
    QPushButton,
    QFrame,
    QSizePolicy,
    QMessageBox,
    QFileDialog,
    QComboBox,
    QStackedWidget,
    QScrollArea
)
from PySide6.QtGui import QImage, QPixmap, QColor
from PySide6.QtCore import Qt, Signal

from .image_preview_dialog import ImagePreviewDialog
from ..common.trend_chart_widget import TrendChartWidget
from ..common.pie_chart_widget import PieChartWidget
from ..common.horizontal_bar_chart_widget import HorizontalBarChartWidget
from ..window_utils import restore_or_center, save_geometry
from modules.configuration.inspection_log_exporter import InspectionLogExporter
from modules.configuration.backup_manager import BackupManager
from modules.configuration.training_data_manager import TrainingDataManager
from modules.utils.logger import get_logger
from modules.utils import accessibility_settings as a11y

app_logger = get_logger()

SETTINGS_KEY = "log_viewer"


class ClickableImageLabel(QLabel):

    doubleClicked = Signal()

    def mouseDoubleClickEvent(self, event):

        self.doubleClicked.emit()

        super().mouseDoubleClickEvent(event)


class LogViewerDialog(QDialog):

    COLUMNS = ["ID", "Zaman", "Model", "Sonuç", "İncelendi"]

    ROI_DETAIL_COLUMNS = ["ROI", "Sonuç", "Tespit Edilen", "Beklenen"]

    def __init__(
        self,
        inspection_logger,
        band_name,
        parent=None,
        operator_name=None,
        band=None
    ):

        super().__init__(parent)

        self.inspection_logger = inspection_logger
        self.band_name = band_name
        self.operator_name = operator_name
        self.band = band
        self.log_exporter = InspectionLogExporter()
        self.backup_manager = BackupManager()
        self.training_data_manager = TrainingDataManager()
        self.rows = []

        self.current_record = None
        self.current_roi_names = []
        self.current_image_path = None
        self.image_dialogs = []

        self.setWindowTitle(f"Inspection Geçmişi - {band_name}")
        restore_or_center(self, SETTINGS_KEY, 1300, 800)

        layout = QVBoxLayout(self)

        top_row = QHBoxLayout()

        top_row.addWidget(QLabel(f"Band: {band_name}"))
        top_row.addStretch()

        self.refresh_button = QPushButton("Yenile")
        self.refresh_button.clicked.connect(self.reload)
        top_row.addWidget(self.refresh_button)

        self.export_excel_button = QPushButton("Excel'e Aktar")
        self.export_excel_button.clicked.connect(self._on_export_excel_clicked)
        top_row.addWidget(self.export_excel_button)

        self.backup_button = QPushButton("Yedekle")
        self.backup_button.clicked.connect(self._on_backup_clicked)
        top_row.addWidget(self.backup_button)

        self.clear_button = QPushButton("Geçmişi Temizle")
        top_row.addWidget(self.clear_button)

        layout.addLayout(top_row)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        records_page = QWidget()
        records_layout = QVBoxLayout(records_page)

        splitter = QSplitter(Qt.Horizontal)
        records_layout.addWidget(splitter)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.itemSelectionChanged.connect(
            self._on_selection_changed
        )
        splitter.addWidget(self.table)

        right_panel = QWidget()
        right_col = QVBoxLayout(right_panel)

        right_col.addWidget(QLabel("Fotoğraf (çift tıkla / büyüt ile aç):"))

        self.image_label = ClickableImageLabel("Fotoğraf yok")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFrameShape(QFrame.Box)
        self.image_label.setMinimumSize(420, 320)
        self.image_label.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        self.image_label.setStyleSheet(
            "background-color: black; color: white;"
        )
        self.image_label.doubleClicked.connect(self._on_enlarge_image)
        right_col.addWidget(self.image_label, stretch=2)

        self.enlarge_image_button = QPushButton("Fotoğrafı Büyüt")
        self.enlarge_image_button.setEnabled(False)
        self.enlarge_image_button.clicked.connect(self._on_enlarge_image)
        right_col.addWidget(self.enlarge_image_button)

        right_col.addWidget(QLabel("ROI Detayları:"))

        self.roi_detail_table = QTableWidget()
        self.roi_detail_table.setColumnCount(len(self.ROI_DETAIL_COLUMNS))
        self.roi_detail_table.setHorizontalHeaderLabels(
            self.ROI_DETAIL_COLUMNS
        )
        self.roi_detail_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.roi_detail_table.verticalHeader().setVisible(False)
        self.roi_detail_table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )
        self.roi_detail_table.setSelectionBehavior(
            QTableWidget.SelectRows
        )
        self.roi_detail_table.itemSelectionChanged.connect(
            self._on_roi_selection_changed
        )
        right_col.addWidget(self.roi_detail_table, stretch=1)

        button_row = QHBoxLayout()

        self.correct_roi_button = QPushButton(
            "Seçili ROI'yi Düzelt (Yanlış Tespit, OK Yap)"
        )
        self.correct_roi_button.setEnabled(False)
        self.correct_roi_button.clicked.connect(
            self._on_correct_roi_clicked
        )
        button_row.addWidget(self.correct_roi_button)

        self.mark_ok_button = QPushButton("Seçili Kaydı İncelendi/OK Yap")
        self.mark_ok_button.setEnabled(False)
        self.mark_ok_button.clicked.connect(self._on_mark_ok_clicked)
        button_row.addWidget(self.mark_ok_button)

        right_col.addLayout(button_row)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        self.tabs.addTab(records_page, "Kayıtlar")

        # ---------- İstatistikler Sekmesi ----------

        stats_page = QWidget()
        stats_layout = QVBoxLayout(stats_page)

        summary_row = QHBoxLayout()

        self.summary_label = QLabel("")
        summary_row.addWidget(self.summary_label, stretch=1)

        stats_layout.addLayout(summary_row)

        overview_row = QHBoxLayout()

        self.overview_pie_chart = PieChartWidget()
        overview_row.addWidget(self.overview_pie_chart, stretch=1)

        trend_column = QVBoxLayout()
        trend_column.addWidget(
            QLabel("Günlük NG Oranı Trendi (son 30 gün):")
        )

        self.trend_chart = TrendChartWidget()
        trend_column.addWidget(self.trend_chart)

        overview_row.addLayout(trend_column, stretch=2)

        stats_layout.addLayout(overview_row)

        # ---------- Vardiya Bazında NG Oranı ----------

        stats_layout.addWidget(
            QLabel("Vardiya Bazlı NG Oranı Trendi (son 20 vardiya):")
        )

        self.shift_trend_chart = TrendChartWidget()
        stats_layout.addWidget(self.shift_trend_chart)

        # ---------- Model Bazında ----------

        model_header_row = QHBoxLayout()
        model_header_row.addWidget(QLabel("Model Bazında:"))
        model_header_row.addStretch()
        model_header_row.addWidget(QLabel("Gösterim:"))

        self.model_view_combo = QComboBox()
        self.model_view_combo.addItems(["Tablo", "Çubuk Grafik"])
        model_header_row.addWidget(self.model_view_combo)

        stats_layout.addLayout(model_header_row)

        self.model_stats_table = QTableWidget()
        self.model_stats_table.setColumnCount(4)
        self.model_stats_table.setHorizontalHeaderLabels(
            ["Model", "OK", "NG", "NG Oranı"]
        )
        self.model_stats_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.model_stats_table.verticalHeader().setVisible(False)
        self.model_stats_table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )

        self.model_bar_chart = HorizontalBarChartWidget()

        model_chart_scroll = QScrollArea()
        model_chart_scroll.setWidgetResizable(True)
        model_chart_scroll.setWidget(self.model_bar_chart)

        self.model_view_stack = QStackedWidget()
        self.model_view_stack.addWidget(self.model_stats_table)
        self.model_view_stack.addWidget(model_chart_scroll)

        self.model_view_combo.currentIndexChanged.connect(
            self.model_view_stack.setCurrentIndex
        )

        stats_layout.addWidget(self.model_view_stack)

        # ---------- ROI Bazında ----------

        roi_header_row = QHBoxLayout()
        roi_header_row.addWidget(QLabel("ROI Bazında (en çok NG üstte):"))
        roi_header_row.addStretch()
        roi_header_row.addWidget(QLabel("Gösterim:"))

        self.roi_view_combo = QComboBox()
        self.roi_view_combo.addItems(["Tablo", "Çubuk Grafik"])
        roi_header_row.addWidget(self.roi_view_combo)

        stats_layout.addLayout(roi_header_row)

        self.roi_stats_table = QTableWidget()
        self.roi_stats_table.setColumnCount(4)
        self.roi_stats_table.setHorizontalHeaderLabels(
            ["ROI", "OK", "NG", "NG Oranı"]
        )
        self.roi_stats_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.roi_stats_table.verticalHeader().setVisible(False)
        self.roi_stats_table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )

        self.roi_bar_chart = HorizontalBarChartWidget()

        roi_chart_scroll = QScrollArea()
        roi_chart_scroll.setWidgetResizable(True)
        roi_chart_scroll.setWidget(self.roi_bar_chart)

        self.roi_view_stack = QStackedWidget()
        self.roi_view_stack.addWidget(self.roi_stats_table)
        self.roi_view_stack.addWidget(roi_chart_scroll)

        self.roi_view_combo.currentIndexChanged.connect(
            self.roi_view_stack.setCurrentIndex
        )

        stats_layout.addWidget(self.roi_view_stack)

        self.tabs.addTab(stats_page, "İstatistikler")

        self.reload()

    # -------------------------------------------------

    def closeEvent(self, event):

        save_geometry(self, SETTINGS_KEY)

        super().closeEvent(event)

    # -------------------------------------------------
    # Excel'e Aktar
    # -------------------------------------------------

    def _on_export_excel_clicked(self):

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Excel'e Aktar",
            f"{self.band_name}_inspection_log.xlsx",
            "Excel Dosyası (*.xlsx)"
        )

        if not path:
            return

        try:

            self.log_exporter.export(
                self.inspection_logger,
                path,
                band_name=self.band_name
            )

        except Exception as e:

            QMessageBox.critical(
                self,
                "Hata",
                f"Excel'e aktarma başarısız: {e}"
            )

            return

        QMessageBox.information(
            self,
            "Başarılı",
            f"Inspection geçmişi şu dosyaya aktarıldı:\n{path}"
        )

    # -------------------------------------------------
    # Yedekle
    # -------------------------------------------------

    def _on_backup_clicked(self):

        if self.band is None:

            QMessageBox.warning(
                self,
                "Uyarı",
                "Yedeklenecek band bilgisi bulunamadı."
            )

            return

        destination = QFileDialog.getExistingDirectory(
            self,
            "Yedekleme Klasörü Seç"
        )

        if not destination:
            return

        try:

            result_folder = self.backup_manager.backup_band(
                self.band,
                destination
            )

        except Exception as e:

            QMessageBox.critical(
                self,
                "Hata",
                f"Yedekleme başarısız: {e}"
            )

            return

        app_logger.info(
            "[%s] band yedeklendi: %s -> %s",
            self.operator_name or "?",
            self.band_name,
            result_folder
        )

        QMessageBox.information(
            self,
            "Başarılı",
            f"Yedek oluşturuldu:\n{result_folder}"
        )

    # -------------------------------------------------
    # Yeniden Yükle
    # -------------------------------------------------

    def reload(self):

        self.rows = self.inspection_logger.fetch_recent(200)

        self.table.setRowCount(len(self.rows))

        for row_index, row in enumerate(self.rows):

            reviewed = bool(row.get("reviewed"))
            ok = row["overall_result"] == "OK"

            if reviewed:
                color = QColor(255, 235, 180)
            elif ok:
                color = QColor(200, 255, 200)
            else:
                color = QColor(255, 200, 200)

            reviewed_text = (
                f"Evet - {row['reviewed_by'] or '?'} "
                f"(orijinal: {row['original_result']})"
                if reviewed
                else "-"
            )

            values = [
                str(row["id"]),
                self._format_timestamp(row["timestamp"]),
                row["model_name"] or "-",
                row["overall_result"],
                reviewed_text
            ]

            for column_index, value in enumerate(values):

                item = QTableWidgetItem(value)
                item.setBackground(color)

                self.table.setItem(
                    row_index,
                    column_index,
                    item
                )

        self.image_label.clear()
        self.image_label.setText("Fotoğraf yok")
        self.current_image_path = None
        self.enlarge_image_button.setEnabled(False)
        self.roi_detail_table.setRowCount(0)
        self.current_record = None
        self.current_roi_names = []
        self.mark_ok_button.setEnabled(False)
        self.correct_roi_button.setEnabled(False)

        self._reload_stats()

    # -------------------------------------------------
    # İstatistikleri Yeniden Yükle
    # -------------------------------------------------

    def _reload_stats(self):

        stats = self.inspection_logger.compute_stats()

        total = stats["total"]
        ok_count = stats["ok_count"]
        ng_count = stats["ng_count"]

        ng_ratio = (ng_count / total * 100) if total else 0.0

        self.summary_label.setText(
            f"Toplam: {total}  |  OK: {ok_count}  |  "
            f"NG: {ng_count}  |  NG Oranı: %{ng_ratio:.1f}"
        )

        self.overview_pie_chart.set_data([
            {
                "label": "OK",
                "value": ok_count,
                "color": QColor(*a11y.get_ok_color_rgb())
            },
            {
                "label": "NG",
                "value": ng_count,
                "color": QColor(*a11y.get_ng_color_rgb())
            }
        ])

        self.trend_chart.set_data(
            self.inspection_logger.compute_daily_trend(30)
        )

        shift_duration_hours = (
            self.band.shift_duration_hours if self.band is not None else 8.0
        )

        self.shift_trend_chart.set_data(
            self.inspection_logger.compute_shift_trend(
                shift_duration_hours, limit_shifts=20
            )
        )

        self._fill_stats_table(self.model_stats_table, stats["by_model"])

        self.model_bar_chart.set_data([
            {"label": name, "ok": counts["ok"], "ng": counts["ng"]}
            for name, counts in sorted(stats["by_model"].items())
        ])

        roi_items = sorted(
            stats["by_roi"].items(),
            key=lambda item: item[1]["ng"],
            reverse=True
        )

        self._fill_stats_table(
            self.roi_stats_table,
            dict(roi_items),
            preserve_order=True
        )

        self.roi_bar_chart.set_data([
            {"label": name, "ok": counts["ok"], "ng": counts["ng"]}
            for name, counts in roi_items
        ])

    # -------------------------------------------------

    def _fill_stats_table(self, table, data, preserve_order=False):

        keys = data.keys() if preserve_order else sorted(data.keys())

        table.setRowCount(len(data))

        for row_index, key in enumerate(keys):

            counts = data[key]

            ok = counts["ok"]
            ng = counts["ng"]
            total = ok + ng

            ratio = (ng / total * 100) if total else 0.0

            values = [key, str(ok), str(ng), f"%{ratio:.1f}"]

            for column_index, value in enumerate(values):

                table.setItem(
                    row_index,
                    column_index,
                    QTableWidgetItem(value)
                )

    # -------------------------------------------------

    def _format_timestamp(self, iso_text):

        try:

            dt = datetime.fromisoformat(iso_text)

            return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")

        except Exception:

            return iso_text

    # -------------------------------------------------
    # Satır Seçimi
    # -------------------------------------------------

    def _on_selection_changed(self):

        selected = self.table.selectedItems()

        if not selected:
            return

        row_index = selected[0].row()

        if row_index < 0 or row_index >= len(self.rows):
            return

        row = self.rows[row_index]

        self._show_detail(row)

        can_mark = (
            row["overall_result"] == "NG"
            and not row.get("reviewed")
        )

        self.mark_ok_button.setEnabled(can_mark)

    # -------------------------------------------------
    # NG Kaydını İncelendi/OK Yap
    # -------------------------------------------------

    def _on_mark_ok_clicked(self):

        selected = self.table.selectedItems()

        if not selected:
            return

        row_index = selected[0].row()

        if row_index < 0 or row_index >= len(self.rows):
            return

        row = self.rows[row_index]

        answer = QMessageBox.question(
            self,
            "Emin misiniz?",
            f"{row['id']} numaralı NG kaydı incelendi olarak "
            f"işaretlenip OK'e çevrilecek. Orijinal NG sonucu "
            f"(ileride model eğitimi için) saklanacak. Devam "
            f"edilsin mi?"
        )

        if answer != QMessageBox.Yes:
            return

        self.inspection_logger.mark_reviewed_ok(
            row["id"],
            operator_name=self.operator_name
        )

        self.reload()

    # -------------------------------------------------
    # ROI Seçimi ve Düzeltme
    # -------------------------------------------------

    def _on_roi_selection_changed(self):

        selected = self.roi_detail_table.selectedItems()

        if not selected or self.current_record is None:
            self.correct_roi_button.setEnabled(False)
            return

        row_index = selected[0].row()

        if row_index < 0 or row_index >= len(self.current_roi_names):
            self.correct_roi_button.setEnabled(False)
            return

        roi_name = self.current_roi_names[row_index]

        try:
            roi_results = json.loads(self.current_record["roi_results"])
        except Exception:
            roi_results = {}

        roi_data = roi_results.get(roi_name, {})

        can_correct = (
            not roi_data.get("ok", True)
            and not roi_data.get("reviewed")
        )

        self.correct_roi_button.setEnabled(can_correct)

    def _on_correct_roi_clicked(self):

        if self.current_record is None:
            return

        selected = self.roi_detail_table.selectedItems()

        if not selected:
            return

        row_index = selected[0].row()

        if row_index < 0 or row_index >= len(self.current_roi_names):
            return

        roi_name = self.current_roi_names[row_index]

        answer = QMessageBox.question(
            self,
            "Emin misiniz?",
            f"{roi_name} yanlış tespit edilmiş (örn. dolu bir göz "
            f"boş görülmüş) kabul edilip OK olarak düzeltilecek. "
            f"Orijinal tespit (model eğitimi için) saklanacak. "
            f"Devam edilsin mi?"
        )

        if answer != QMessageBox.Yes:
            return

        record_id = self.current_record["id"]

        self.inspection_logger.correct_roi(
            record_id,
            roi_name,
            True,
            operator_name=self.operator_name
        )

        # Bu ROI için eğitim verisi kaydedilmişse (bkz.
        # TrainingDataManager), otomatik yeniden etiketleme YAPMIYORUZ -
        # bir düzeltme görsel tespit hatası da olabilir, model
        # yapılandırma farkı da. Sadece "elle gözden geçirilmeli" diye
        # işaretliyoruz.
        training_image_paths = self.inspection_logger.get_training_image_paths(
            record_id
        )
        roi_training_images = training_image_paths.get(roi_name)

        if roi_training_images:
            self.training_data_manager.flag_for_review(roi_training_images)

        self.reload()

    # -------------------------------------------------

    def _show_detail(self, row):

        self.current_record = row

        try:
            roi_results = json.loads(row["roi_results"])
        except Exception:
            roi_results = {}

        self.current_roi_names = sorted(roi_results.keys())

        self.roi_detail_table.setRowCount(len(self.current_roi_names))

        for row_index, name in enumerate(self.current_roi_names):

            data = roi_results[name]

            ok = bool(data.get("ok"))

            reviewed = bool(data.get("reviewed"))

            color = (
                QColor(255, 235, 180)
                if reviewed
                else QColor(200, 255, 200) if ok else QColor(255, 200, 200)
            )

            values = [
                name,
                "OK" if ok else "NG",
                str(data.get("state")),
                str(data.get("expected"))
            ]

            for column_index, value in enumerate(values):

                item = QTableWidgetItem(value)
                item.setBackground(color)

                self.roi_detail_table.setItem(
                    row_index,
                    column_index,
                    item
                )

        self.correct_roi_button.setEnabled(False)

        self._show_image(row.get("image_path"))

    # -------------------------------------------------

    def _show_image(self, image_path):

        self.current_image_path = image_path

        if not image_path:

            self.image_label.clear()
            self.image_label.setText("Fotoğraf yok")
            self.enlarge_image_button.setEnabled(False)
            return

        image = cv2.imread(image_path)

        if image is None:

            self.image_label.clear()
            self.image_label.setText("Fotoğraf okunamadı")
            self.enlarge_image_button.setEnabled(False)
            return

        self.enlarge_image_button.setEnabled(True)

        height, width = image.shape[:2]

        rgb = image[:, :, ::-1].copy()

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

        pixmap = QPixmap.fromImage(qimage).scaled(
            self.image_label.width(),
            self.image_label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.image_label.setPixmap(pixmap)

    # -------------------------------------------------
    # Fotoğrafı Büyüt
    # -------------------------------------------------

    def _on_enlarge_image(self):

        if not self.current_image_path:
            return

        record_id = (
            self.current_record["id"]
            if self.current_record is not None
            else "-"
        )

        dialog = ImagePreviewDialog(
            self.current_image_path,
            title=f"Fotoğraf - Kayıt #{record_id}",
            parent=self
        )

        self.image_dialogs.append(dialog)

        dialog.finished.connect(
            lambda _: self.image_dialogs.remove(dialog)
            if dialog in self.image_dialogs
            else None
        )

        dialog.show()
