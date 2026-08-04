import numpy as np

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
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
    DOLU (FULL) olması gerektiği. Listede olmayan her ROI
    otomatik olarak BOŞ (EMPTY) kabul edilir.

    Beklenen durum hem sağdaki işaretli liste hem de referans
    fotoğrafı üzerindeki ROI'lere tıklanarak seçilebilir; ikisi
    birbiriyle senkronize kalır.

    Controller'ın kullandığı public metodlar:

        set_models(models: list[dict])
        get_selected_model_id() -> str | None
        set_reference_image(image)
        set_roi_shapes(rois: list[dict])
        set_roi_checklist(roi_names, checked_names)
        get_checked_rois() -> list[str]
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

        self.roi_checklist = QListWidget()
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

        for i in range(self.roi_checklist.count()):

            item = self.roi_checklist.item(i)

            if item.text() == name:

                item.setCheckState(
                    Qt.Unchecked
                    if item.checkState() == Qt.Checked
                    else Qt.Checked
                )

                return

    def _on_checklist_item_changed(self, item: QListWidgetItem):

        roi_item = self.roi_items.get(item.text())

        if roi_item is not None:
            roi_item.apply_state(item.checkState() == Qt.Checked)

    def _sync_preview_colors(self):

        checked = set(self.get_checked_rois())

        for name, roi_item in self.roi_items.items():
            roi_item.apply_state(name in checked)

    # -------------------------------------------------
    # Beklenen Durum (ROI Checklist)
    # -------------------------------------------------

    def set_roi_checklist(self, roi_names: list, checked_names: list):

        checked_set = set(checked_names)

        self.roi_checklist.blockSignals(True)

        self.roi_checklist.clear()

        for name in roi_names:

            item = QListWidgetItem(name)

            item.setFlags(
                item.flags() | Qt.ItemIsUserCheckable
            )

            item.setCheckState(
                Qt.Checked
                if name in checked_set
                else Qt.Unchecked
            )

            self.roi_checklist.addItem(item)

        self.roi_checklist.blockSignals(False)

        self._sync_preview_colors()

    def get_checked_rois(self) -> list:

        checked = []

        for i in range(self.roi_checklist.count()):

            item = self.roi_checklist.item(i)

            if item.checkState() == Qt.Checked:

                checked.append(item.text())

        return checked

    def clear_roi_checklist(self):

        self.roi_checklist.clear()

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
