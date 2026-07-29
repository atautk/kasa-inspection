import uuid

import numpy as np

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPolygonItem,
    QGraphicsPixmapItem,
    QGraphicsSimpleTextItem,
    QGraphicsItem
)
from PySide6.QtGui import (
    QImage,
    QPixmap,
    QPolygonF,
    QPen,
    QBrush,
    QColor
)
from PySide6.QtCore import Qt, QPointF


class ROIPolygonItem(QGraphicsPolygonItem):
    """
    Tek bir ROI'yi (göz) temsil eden polygon.
    Seçilebilir ve sürüklenebilir.
    """

    NORMAL_COLOR = QColor(0, 200, 0)
    SELECTED_COLOR = QColor(220, 30, 30)

    def __init__(self, roi_id: str, name: str, points):

        polygon = QPolygonF(
            [QPointF(x, y) for x, y in points]
        )

        super().__init__(polygon)

        self.roi_id = roi_id
        self.roi_name = name

        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

        self.setPen(QPen(self.NORMAL_COLOR, 2))
        self.setBrush(QBrush(QColor(0, 200, 0, 40)))

        self.label = QGraphicsSimpleTextItem(name, self)
        self.label.setBrush(QBrush(self.NORMAL_COLOR))

        self._update_label_position()

    # -------------------------------------------------

    def _update_label_position(self):

        rect = self.polygon().boundingRect()

        self.label.setPos(
            rect.x(),
            rect.y() - 18
        )

    # -------------------------------------------------

    def set_name(self, name: str):

        self.roi_name = name
        self.label.setText(name)
        self._update_label_position()

    # -------------------------------------------------

    def itemChange(self, change, value):

        if change == QGraphicsItem.ItemSelectedHasChanged:

            color = (
                self.SELECTED_COLOR
                if value
                else self.NORMAL_COLOR
            )

            self.setPen(QPen(color, 2))
            self.label.setBrush(QBrush(color))

        return super().itemChange(change, value)

    # -------------------------------------------------

    def scene_points(self):

        points = []

        for i in range(self.polygon().count()):

            p = self.mapToScene(self.polygon().at(i))

            points.append([p.x(), p.y()])

        return points


class ROIGraphicsView(QGraphicsView):
    """
    Fare/klavye olaylarını ROIPage'e ileten görünüm.
    Kendisi hiçbir ROI mantığı bilmez.
    """

    def __init__(self, page):

        super().__init__(page.scene)

        self.page = page

        self.setDragMode(QGraphicsView.NoDrag)
        self.setRenderHint(self.renderHints())

    # -------------------------------------------------

    def mousePressEvent(self, event):

        if self.page.drawing_mode:

            scene_pos = self.mapToScene(event.pos())

            if event.button() == Qt.LeftButton:

                self.page.add_draw_point(scene_pos)
                return

            if event.button() == Qt.RightButton:

                self.page.finish_polygon()
                return

        super().mousePressEvent(event)

    # -------------------------------------------------

    def keyPressEvent(self, event):

        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):

            self.page.delete_selected()
            return

        super().keyPressEvent(event)


class ROIPage(QWidget):
    """
    ROI Editor sekmesi.

    Bu sınıf SADECE UI ve görsel state'ten sorumludur.
    roi.json okuma/yazma işini bilmez, bunu Controller yapar.

    Controller'ın kullandığı public metodlar:

        set_background(image)
        load_rois(rois: list[dict])
        get_rois() -> list[dict]
        clear()
        set_status(text)

    Controller'ın dinlediği sinyal:

        save_button.clicked
    """

    def __init__(self):

        super().__init__()

        self.scene = QGraphicsScene()
        self.background_item = None
        self.polygon_items = []

        self.drawing_mode = False
        self.temp_points = []
        self.temp_markers = []

        layout = QVBoxLayout(self)

        # ---------- Bilgi ----------

        self.status_label = QLabel(
            "Reference yüklenmedi."
        )
        layout.addWidget(self.status_label)

        self.info_label = QLabel(
            "ROI Sayısı: 0"
        )
        layout.addWidget(self.info_label)

        # ---------- Görüntü ----------

        self.view = ROIGraphicsView(self)
        self.view.setMinimumSize(800, 600)
        layout.addWidget(self.view)

        # ---------- Butonlar ----------

        button_row = QHBoxLayout()

        self.new_roi_button = QPushButton("Yeni ROI")
        self.new_roi_button.setCheckable(True)
        self.new_roi_button.clicked.connect(
            self.toggle_drawing_mode
        )
        button_row.addWidget(self.new_roi_button)

        self.delete_button = QPushButton("Sil")
        self.delete_button.clicked.connect(
            self.delete_selected
        )
        button_row.addWidget(self.delete_button)

        self.save_button = QPushButton("Kaydet")
        button_row.addWidget(self.save_button)

        layout.addLayout(button_row)

    # -------------------------------------------------
    # Arka Plan (Reference)
    # -------------------------------------------------

    def set_background(self, image: np.ndarray):

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

        if self.background_item is not None:
            self.scene.removeItem(self.background_item)

        self.background_item = QGraphicsPixmapItem(pixmap)
        self.background_item.setZValue(-1)

        self.scene.addItem(self.background_item)
        self.scene.setSceneRect(0, 0, width, height)

        self.view.fitInView(
            self.background_item,
            Qt.KeepAspectRatio
        )

        self.set_status("Reference yüklendi.")

    # -------------------------------------------------
    # ROI Yükleme / Okuma
    # -------------------------------------------------

    def load_rois(self, rois: list):

        for item in self.polygon_items:
            self.scene.removeItem(item)

        self.polygon_items = []

        for roi in rois:

            item = ROIPolygonItem(
                roi.get("id", "") or self._generate_id(),
                roi.get("name", ""),
                roi.get("points", [])
            )

            self.scene.addItem(item)
            self.polygon_items.append(item)

        self._update_info()

    def get_rois(self) -> list:

        return [
            {
                "id": item.roi_id,
                "name": item.roi_name,
                "points": item.scene_points()
            }
            for item in self.polygon_items
        ]

    def clear(self):

        for item in self.polygon_items:
            self.scene.removeItem(item)

        self.polygon_items = []

        if self.background_item is not None:
            self.scene.removeItem(self.background_item)
            self.background_item = None

        self._cancel_drawing()

        self._update_info()

    # -------------------------------------------------
    # Çizim Modu
    # -------------------------------------------------

    def toggle_drawing_mode(self, checked: bool):

        self.drawing_mode = checked

        if checked:

            self.new_roi_button.setText(
                "İptal (Sağ Tık: Bitir)"
            )

            self.set_status(
                "Noktaları tıklayın, bitirmek için sağ tık."
            )

        else:

            self.new_roi_button.setText("Yeni ROI")
            self._cancel_drawing()

    def add_draw_point(self, scene_pos):

        self.temp_points.append(
            [scene_pos.x(), scene_pos.y()]
        )

        marker = self.scene.addEllipse(
            scene_pos.x() - 3,
            scene_pos.y() - 3,
            6,
            6,
            QPen(QColor(30, 100, 220)),
            QBrush(QColor(30, 100, 220))
        )

        self.temp_markers.append(marker)

    def finish_polygon(self):

        if len(self.temp_points) < 3:

            self.set_status("En az 3 nokta gerekli.")
            return

        name = f"G{len(self.polygon_items) + 1:02d}"

        item = ROIPolygonItem(
            roi_id=self._generate_id(),
            name=name,
            points=self.temp_points
        )

        self.scene.addItem(item)
        self.polygon_items.append(item)

        self._cancel_drawing()

        self.new_roi_button.setChecked(False)
        self.new_roi_button.setText("Yeni ROI")
        self.drawing_mode = False

        self.set_status(f"{name} eklendi.")

        self._update_info()

    def _cancel_drawing(self):

        for marker in self.temp_markers:
            self.scene.removeItem(marker)

        self.temp_markers = []
        self.temp_points = []

    # -------------------------------------------------
    # Silme
    # -------------------------------------------------

    def delete_selected(self):

        selected = [
            item for item in self.polygon_items
            if item.isSelected()
        ]

        if not selected:
            return

        for item in selected:

            self.scene.removeItem(item)
            self.polygon_items.remove(item)

        self._update_info()

        self.set_status(f"{len(selected)} ROI silindi.")

    # -------------------------------------------------
    # Yardımcı
    # -------------------------------------------------

    def set_status(self, text: str):

        self.status_label.setText(text)

    def _update_info(self):

        self.info_label.setText(
            f"ROI Sayısı: {len(self.polygon_items)}"
        )

    def _generate_id(self):

        return str(uuid.uuid4())

    # -------------------------------------------------
    # Pencere Yeniden Boyutlanınca
    # -------------------------------------------------

    def resizeEvent(self, event):

        super().resizeEvent(event)

        if self.background_item is not None:

            self.view.fitInView(
                self.background_item,
                Qt.KeepAspectRatio
            )