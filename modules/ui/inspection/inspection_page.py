import numpy as np

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QFrame,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView
)
from PySide6.QtGui import QImage, QPixmap, QColor
from PySide6.QtCore import Qt


class InspectionPage(QWidget):
    """
    Inspection ekranı.

    Bu sınıf SADECE UI'dan sorumludur.
    Kamera, OpenCV, ArUco veya inspection mantığı hakkında hiçbir şey bilmez.

    Controller, aşağıdaki public metodları çağırarak bu sayfayı günceller:

        set_band_list(names: list[str])
        set_model_list(names: list[str])
        set_image(frame)
        clear_image()
        set_results(results: dict)
        clear_results()
        set_mode(text)
        set_confidence(value)
        set_performance(fps, inspection_time_ms)
        set_status(text)
        set_start_button_text(text)
        set_debug_button_text(text)
        enable_selection(enabled: bool)
        show_ng_alert()
        hide_ng_alert()

    Controller'ın dinlediği sinyaller:

        band_combo.currentIndexChanged
        model_combo.currentIndexChanged
        start_button.clicked
        save_reference_button.clicked
        debug_button.clicked
        history_button.clicked
    """

    COLUMNS = [
        "ROI",
        "Durum",
        "Beklenen",
        "Sonuç",
        "Fark %",
        "Piksel"
    ]

    def __init__(self):

        super().__init__()

        root = QVBoxLayout(self)

        # ---------- NG Uyarı Bannerı ----------

        self.ng_banner = QLabel("⚠ NG !")
        self.ng_banner.setAlignment(Qt.AlignCenter)
        self.ng_banner.setStyleSheet(
            "background-color: #cc0000; color: white; "
            "font-size: 22px; font-weight: bold; padding: 10px;"
        )
        self.ng_banner.hide()
        root.addWidget(self.ng_banner)

        # ---------- Üst Seçim Satırı ----------

        selection_row = QHBoxLayout()

        selection_row.addWidget(QLabel("Band:"))

        self.band_combo = QComboBox()
        selection_row.addWidget(self.band_combo)

        selection_row.addWidget(QLabel("Model:"))

        self.model_combo = QComboBox()
        selection_row.addWidget(self.model_combo)

        selection_row.addStretch()

        self.start_button = QPushButton("Başlat")
        selection_row.addWidget(self.start_button)

        self.save_reference_button = QPushButton("Reference Kaydet")
        selection_row.addWidget(self.save_reference_button)

        self.debug_button = QPushButton("Debug Göster")
        selection_row.addWidget(self.debug_button)

        self.history_button = QPushButton("Geçmiş")
        selection_row.addWidget(self.history_button)

        root.addLayout(selection_row)

        # ---------- Orta Alan (Görüntü + Tablo) ----------

        middle_row = QHBoxLayout()

        self.image_label = QLabel("Kamera kapalı")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFrameShape(QFrame.Box)
        self.image_label.setMinimumSize(640, 480)
        self.image_label.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        self.image_label.setStyleSheet(
            "background-color: black; color: white;"
        )
        middle_row.addWidget(self.image_label, stretch=2)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(len(self.COLUMNS))
        self.results_table.setHorizontalHeaderLabels(self.COLUMNS)
        self.results_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )
        self.results_table.setMinimumWidth(420)
        middle_row.addWidget(self.results_table, stretch=1)

        root.addLayout(middle_row, stretch=1)

        # ---------- Alt Bilgi Satırı ----------

        info_row = QHBoxLayout()

        self.mode_label = QLabel("Mode: -")
        info_row.addWidget(self.mode_label)

        self.confidence_label = QLabel("Confidence: -")
        info_row.addWidget(self.confidence_label)

        self.performance_label = QLabel("FPS: - | Süre: -")
        info_row.addWidget(self.performance_label)

        info_row.addStretch()

        self.status_label = QLabel("Durum: -")
        info_row.addWidget(self.status_label)

        root.addLayout(info_row)

    # -------------------------------------------------
    # Band / Model Listeleri
    # -------------------------------------------------

    def set_band_list(self, names: list[str]):

        self.band_combo.blockSignals(True)
        self.band_combo.clear()
        self.band_combo.addItems(names)
        self.band_combo.blockSignals(False)

    def set_model_list(self, names: list[str]):

        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItems(names)
        self.model_combo.blockSignals(False)

    def enable_selection(self, enabled: bool):

        self.band_combo.setEnabled(enabled)
        self.model_combo.setEnabled(enabled)

    # -------------------------------------------------
    # Görüntü
    # -------------------------------------------------

    def set_image(self, frame: np.ndarray):

        if frame is None:
            return

        height, width = frame.shape[:2]

        rgb = frame[:, :, ::-1].copy()

        image = QImage(
            rgb.data,
            width,
            height,
            rgb.strides[0],
            QImage.Format_RGB888
        )

        pixmap = QPixmap.fromImage(image).scaled(
            self.image_label.width(),
            self.image_label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.image_label.setPixmap(pixmap)

    def clear_image(self):

        self.image_label.clear()
        self.image_label.setText("Kamera kapalı")

    # -------------------------------------------------
    # Sonuç Tablosu
    # -------------------------------------------------

    def set_results(self, results: dict):

        rows = sorted(results.items())

        self.results_table.setRowCount(len(rows))

        for row_index, (roi_name, data) in enumerate(rows):

            ok = bool(data.get("ok", False))

            color = QColor(200, 255, 200) if ok else QColor(255, 200, 200)

            values = [
                roi_name,
                str(data.get("state", "-")),
                str(data.get("expected", "-")),
                "OK" if ok else "NG",
                f"{data.get('change_ratio', 0):.2f}",
                str(data.get("changed_pixels", 0))
            ]

            for column_index, value in enumerate(values):

                item = QTableWidgetItem(value)
                item.setBackground(color)

                self.results_table.setItem(
                    row_index,
                    column_index,
                    item
                )

    def clear_results(self):

        self.results_table.setRowCount(0)

    # -------------------------------------------------
    # Bilgi Etiketleri
    # -------------------------------------------------

    def set_mode(self, text: str):

        self.mode_label.setText(f"Mode: {text}")

    def set_confidence(self, value):

        self.confidence_label.setText(f"Confidence: {value}")

    def set_performance(self, fps: float, inspection_time_ms: float):

        self.performance_label.setText(
            f"FPS: {fps:.1f} | Süre: {inspection_time_ms:.1f} ms"
        )

    def set_status(self, text: str):

        self.status_label.setText(f"Durum: {text}")

    # -------------------------------------------------
    # Buton Metinleri
    # -------------------------------------------------

    def set_start_button_text(self, text: str):

        self.start_button.setText(text)

    def set_debug_button_text(self, text: str):

        self.debug_button.setText(text)

    # -------------------------------------------------
    # NG Uyarısı
    # -------------------------------------------------

    def show_ng_alert(self):

        self.ng_banner.show()

    def hide_ng_alert(self):

        self.ng_banner.hide()
