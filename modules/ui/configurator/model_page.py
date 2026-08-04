import numpy as np

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLineEdit,
    QPushButton,
    QLabel,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsPolygonItem,
    QGraphicsSimpleTextItem
)
from PySide6.QtGui import QImage, QPixmap, QPolygonF, QPen, QBrush, QColor
from PySide6.QtCore import Qt, QPointF


class ModelROIPreviewItem(QGraphicsPolygonItem):
    """
    Referans fotoğrafı üzerinde tek bir ROI'yi gösteren, tıklanarak
    DOLU/BOŞ durumunu değiştirebilen önizleme şekli. Sürükleme veya
    şekil değişikliği yapılamaz; sadece tıklama ile durum değiştirir.
    """

    FULL_COLOR = QColor(0, 200, 0)
    EMPTY_COLOR = QColor(150, 150, 150)

    def __init__(self, page, name: str, points):

        polygon = QPolygonF(
            [QPointF(x, y) for x, y in points]
        )

        super().__init__(polygon)

        self.page = page
        self.roi_name = name

        self.label = QGraphicsSimpleTextItem(name, self)

        self.apply_state(False)

    # -------------------------------------------------

    def apply_state(self, full: bool):

        color = self.FULL_COLOR if full else self.EMPTY_COLOR

        self.setPen(QPen(color, 2))
        self.setBrush(
            QBrush(QColor(color.red(), color.green(), color.blue(), 60))
        )
        self.label.setBrush(QBrush(color))

        rect = self.polygon().boundingRect()

        self.label.setPos(rect.x(), rect.y() - 18)

    # -------------------------------------------------

    def mousePressEvent(self, event):

        self.page.toggle_roi(self.roi_name)

        event.accept()


class ModelPage(QWidget):
    """
    Model Editor sekmesi.

    Bu sınıf SADECE UI'dan sorumludur. Dosya okuma/yazma
    (models/*.json) işini bilmez, bunu Controller yapar.

    Bir "Model" = isim (Clio, Duster, ...) + hangi ROI'lerin
    DOLU (FULL) olması gerektiği + (opsiyonel) ROI başına özel
    değişim eşiği. Listede olmayan her ROI otomatik olarak BOŞ
    (EMPTY) kabul edilir; eşik override boş bırakılırsa bandın
    genel eşiği kullanılır.

    Beklenen durum hem sağdaki tablodan hem de referans fotoğrafı
    üzerindeki ROI'lere tıklanarak seçilebilir; ikisi birbiriyle
    senkronize kalır.

    Controller'ın kullandığı public metodlar:

        set_models(models: list[dict])
        get_selected_model_id() -> str | None
        set_reference_image(image)
        set_roi_shapes(rois: list[dict])
        set_roi_checklist(roi_names, checked_names, thresholds=None)
        get_checked_rois() -> list[str]
        get_roi_thresholds() -> dict[str, float]
        clear_roi_checklist()
        set_status(text)

    Controller'ın dinlediği sinyaller:

        new_button.clicked
        delete_button.clicked
        save_button.clicked
        model_list.currentItemChanged
    """

    def __init__(self):

        super().__init__()

        layout = QHBoxLayout(self)

        # ---------- Sol : Model Listesi ----------

        left_column = QVBoxLayout()

        left_column.addWidget(QLabel("Modeller"))

        self.model_list = QListWidget()
        left_column.addWidget(self.model_list)

        model_buttons = QHBoxLayout()

        self.new_button = QPushButton("Yeni Model")
        model_buttons.addWidget(self.new_button)

        self.delete_button = QPushButton("Sil")
        model_buttons.addWidget(self.delete_button)

        left_column.addLayout(model_buttons)

        layout.addLayout(left_column, 1)

        # ---------- Sağ : Beklenen Durum ----------

        right_column = QVBoxLayout()

        right_column.addWidget(
            QLabel(
                "Beklenen Durum (İşaretli = DOLU) — "
                "listeden veya fotoğraftaki ROI'ye tıklayarak seçin"
            )
        )

        self.preview_scene = QGraphicsScene()
        self.preview_background = None
        self.roi_items = {}

        self.preview_view = QGraphicsView(self.preview_scene)
        self.preview_view.setMinimumSize(480, 360)
        right_column.addWidget(self.preview_view, stretch=2)

        right_column.addWidget(
            QLabel(
                "Eşik Override sütunu boş bırakılırsa bandın genel "
                "değişim eşiği kullanılır."
            )
        )

        self.roi_checklist = QTableWidget()
        self.roi_checklist.setColumnCount(3)
        self.roi_checklist.setHorizontalHeaderLabels(
            ["DOLU", "ROI", "Eşik Override (%)"]
        )
        self.roi_checklist.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        self.roi_checklist.verticalHeader().setVisible(False)
        self.roi_checklist.itemChanged.connect(
            self._on_checklist_item_changed
        )
        right_column.addWidget(self.roi_checklist, stretch=1)

        self.status_label = QLabel("-")
        right_column.addWidget(self.status_label)

        self.save_button = QPushButton("Kaydet")
        right_column.addWidget(self.save_button)

        layout.addLayout(right_column, 2)

    # -------------------------------------------------
    # Model Listesi
    # -------------------------------------------------

    def set_models(self, models: list):

        self.model_list.clear()

        for model in models:

            item = QListWidgetItem(model["name"])

            item.setData(Qt.UserRole, model["id"])

            self.model_list.addItem(item)

    def get_selected_model_id(self):

        item = self.model_list.currentItem()

        if item is None:
            return None

        return item.data(Qt.UserRole)

    # -------------------------------------------------
    # Referans Fotoğrafı Önizleme
    # -------------------------------------------------

    def set_reference_image(self, image: np.ndarray | None):

        if self.preview_background is not None:
            self.preview_scene.removeItem(self.preview_background)
            self.preview_background = None

        if image is None:
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

        pixmap = QPixmap.fromImage(qimage)

        self.preview_background = QGraphicsPixmapItem(pixmap)
        self.preview_background.setZValue(-1)

        self.preview_scene.addItem(self.preview_background)
        self.preview_scene.setSceneRect(0, 0, width, height)

        self.preview_view.fitInView(
            self.preview_background,
            Qt.KeepAspectRatio
        )

    def set_roi_shapes(self, rois: list):

        for item in self.roi_items.values():
            self.preview_scene.removeItem(item)

        self.roi_items = {}

        for roi in rois:

            name = roi.get("name", "")

            item = ModelROIPreviewItem(
                self,
                name,
                roi.get("points", [])
            )

            self.preview_scene.addItem(item)
            self.roi_items[name] = item

        self._sync_preview_colors()

    def toggle_roi(self, name: str):

        for row in range(self.roi_checklist.rowCount()):

            name_item = self.roi_checklist.item(row, 1)

            if name_item is not None and name_item.text() == name:

                check_item = self.roi_checklist.item(row, 0)

                check_item.setCheckState(
                    Qt.Unchecked
                    if check_item.checkState() == Qt.Checked
                    else Qt.Checked
                )

                return

    def _on_checklist_item_changed(self, item: QTableWidgetItem):

        if item.column() != 0:
            return

        name_item = self.roi_checklist.item(item.row(), 1)

        if name_item is None:
            return

        roi_item = self.roi_items.get(name_item.text())

        if roi_item is not None:
            roi_item.apply_state(item.checkState() == Qt.Checked)

    def _sync_preview_colors(self):

        checked = set(self.get_checked_rois())

        for name, roi_item in self.roi_items.items():
            roi_item.apply_state(name in checked)

    # -------------------------------------------------
    # Beklenen Durum (ROI Tablosu: DOLU / Eşik Override)
    # -------------------------------------------------

    def set_roi_checklist(
        self,
        roi_names: list,
        checked_names: list,
        thresholds: dict = None
    ):

        thresholds = thresholds or {}
        checked_set = set(checked_names)

        self.roi_checklist.blockSignals(True)

        self.roi_checklist.setRowCount(len(roi_names))

        for row, name in enumerate(roi_names):

            check_item = QTableWidgetItem()
            check_item.setFlags(
                Qt.ItemIsUserCheckable | Qt.ItemIsEnabled
            )
            check_item.setCheckState(
                Qt.Checked
                if name in checked_set
                else Qt.Unchecked
            )
            self.roi_checklist.setItem(row, 0, check_item)

            name_item = QTableWidgetItem(name)
            name_item.setFlags(
                name_item.flags() & ~Qt.ItemIsEditable
            )
            self.roi_checklist.setItem(row, 1, name_item)

            threshold_input = QLineEdit()
            threshold_input.setPlaceholderText("varsayılan")

            if name in thresholds:
                threshold_input.setText(str(thresholds[name]))

            self.roi_checklist.setCellWidget(row, 2, threshold_input)

        self.roi_checklist.blockSignals(False)

        self._sync_preview_colors()

    def get_checked_rois(self) -> list:

        checked = []

        for row in range(self.roi_checklist.rowCount()):

            check_item = self.roi_checklist.item(row, 0)
            name_item = self.roi_checklist.item(row, 1)

            if (
                check_item is not None
                and name_item is not None
                and check_item.checkState() == Qt.Checked
            ):
                checked.append(name_item.text())

        return checked

    def get_roi_thresholds(self) -> dict:

        thresholds = {}

        for row in range(self.roi_checklist.rowCount()):

            name_item = self.roi_checklist.item(row, 1)
            widget = self.roi_checklist.cellWidget(row, 2)

            if name_item is None or widget is None:
                continue

            text = widget.text().strip()

            if not text:
                continue

            try:
                thresholds[name_item.text()] = float(text)
            except ValueError:
                continue

        return thresholds

    def clear_roi_checklist(self):

        self.roi_checklist.setRowCount(0)

        self._sync_preview_colors()

    # -------------------------------------------------
    # Yardımcı
    # -------------------------------------------------

    def set_status(self, text: str):

        self.status_label.setText(text)

    # -------------------------------------------------
    # Pencere Yeniden Boyutlanınca
    # -------------------------------------------------

    def resizeEvent(self, event):

        super().resizeEvent(event)

        if self.preview_background is not None:

            self.preview_view.fitInView(
                self.preview_background,
                Qt.KeepAspectRatio
            )
