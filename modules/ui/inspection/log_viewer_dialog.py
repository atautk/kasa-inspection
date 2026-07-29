import json
from datetime import datetime

import cv2

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLabel,
    QPushButton,
    QFrame,
    QSizePolicy
)
from PySide6.QtGui import QImage, QPixmap, QColor
from PySide6.QtCore import Qt


class LogViewerDialog(QDialog):

    COLUMNS = ["ID", "Zaman", "Model", "Sonuç"]

    def __init__(self, inspection_logger, band_name, parent=None):

        super().__init__(parent)

        self.inspection_logger = inspection_logger
        self.rows = []

        self.setWindowTitle(f"Inspection Geçmişi - {band_name}")
        self.resize(900, 500)

        layout = QVBoxLayout(self)

        top_row = QHBoxLayout()

        top_row.addWidget(QLabel(f"Band: {band_name}"))
        top_row.addStretch()

        self.refresh_button = QPushButton("Yenile")
        self.refresh_button.clicked.connect(self.reload)
        top_row.addWidget(self.refresh_button)

        self.clear_button = QPushButton("Geçmişi Temizle")
        top_row.addWidget(self.clear_button)

        layout.addLayout(top_row)

        content_row = QHBoxLayout()

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
        content_row.addWidget(self.table, stretch=2)

        right_col = QVBoxLayout()

        self.image_label = QLabel("Fotoğraf yok")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFrameShape(QFrame.Box)
        self.image_label.setMinimumSize(320, 240)
        self.image_label.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        self.image_label.setStyleSheet(
            "background-color: black; color: white;"
        )
        right_col.addWidget(self.image_label)

        self.detail_label = QLabel("")
        self.detail_label.setWordWrap(True)
        right_col.addWidget(self.detail_label)

        content_row.addLayout(right_col, stretch=1)

        layout.addLayout(content_row)

        self.reload()

    # -------------------------------------------------
    # Yeniden Yükle
    # -------------------------------------------------

    def reload(self):

        self.rows = self.inspection_logger.fetch_recent(200)

        self.table.setRowCount(len(self.rows))

        for row_index, row in enumerate(self.rows):

            ok = row["overall_result"] == "OK"

            color = QColor(200, 255, 200) if ok else QColor(255, 200, 200)

            values = [
                str(row["id"]),
                self._format_timestamp(row["timestamp"]),
                row["model_name"] or "-",
                row["overall_result"]
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
        self.detail_label.setText("")

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

        self._show_detail(self.rows[row_index])

    # -------------------------------------------------

    def _show_detail(self, row):

        try:
            roi_results = json.loads(row["roi_results"])
        except Exception:
            roi_results = {}

        lines = []

        for name, data in sorted(roi_results.items()):

            status = "OK" if data.get("ok") else "NG"

            lines.append(
                f"{name}: {status} "
                f"({data.get('state')}, beklenen {data.get('expected')})"
            )

        self.detail_label.setText("\n".join(lines))

        self._show_image(row.get("image_path"))

    # -------------------------------------------------

    def _show_image(self, image_path):

        if not image_path:

            self.image_label.clear()
            self.image_label.setText("Fotoğraf yok")
            return

        image = cv2.imread(image_path)

        if image is None:

            self.image_label.clear()
            self.image_label.setText("Fotoğraf okunamadı")
            return

        height, width = image.shape[:2]

        rgb = image[:, :, ::-1].copy()

        qimage = QImage(
            rgb.data,
            width,
            height,
            rgb.strides[0],
            QImage.Format_RGB888
        )

        pixmap = QPixmap.fromImage(qimage).scaled(
            self.image_label.width(),
            self.image_label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.image_label.setPixmap(pixmap)
