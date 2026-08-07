import uuid

import numpy as np

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPolygonItem,
    QGraphicsPixmapItem,
    QGraphicsSimpleTextItem,
    QGraphicsEllipseItem,
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


class ROIVertexHandle(QGraphicsEllipseItem):
    """
    Bir ROI köşe noktasını temsil eden, sürüklenerek o noktayı
    yeniden konumlandıran (boyutlandırma/yeniden şekillendirme)
    küçük tutamaç. ROIPolygonItem'ın çocuğu olarak eklenir; bu
    sayede tüm ROI sürüklenince tutamaçlar otomatik takip eder,
    ROI silinince de otomatik temizlenir.

    Fare olaylarını (ItemIsMovable yerine) kendi mousePress/Move/
    ReleaseEvent'leriyle bilinçli olarak yönetir ve event.accept()
    çağırır. Aksi halde, altındaki poligon da ItemIsMovable
    olduğundan Qt hangisinin sürükleneceğine tutarsız karar
    verebiliyor; bazen tutamaç yerine tüm ROI kayıyor, bazen de
    hiçbir şey olmuyordu.
    """

    SIZE = 10
    COLOR = QColor(255, 190, 0)
    BORDER_COLOR = QColor(120, 90, 0)

    def __init__(self, roi_item, index: int):

        half = self.SIZE / 2

        super().__init__(-half, -half, self.SIZE, self.SIZE)

        self.roi_item = roi_item
        self.index = index

        self.setPen(QPen(self.BORDER_COLOR, 1))
        self.setBrush(QBrush(self.COLOR))
        self.setZValue(10)
        self.setCursor(Qt.CrossCursor)
        self.setAcceptedMouseButtons(Qt.LeftButton)

    # -------------------------------------------------

    def mousePressEvent(self, event):

        event.accept()

    def mouseMoveEvent(self, event):

        new_pos = self.mapToParent(event.pos())

        self.setPos(new_pos)
        self.roi_item.update_vertex(self.index, new_pos)

        event.accept()

    def mouseReleaseEvent(self, event):

        event.accept()


class ROIPolygonItem(QGraphicsPolygonItem):
    """
    Tek bir ROI'yi (göz) temsil eden polygon.
    Seçilebilir, sürüklenebilir (taşıma) ve seçiliyken köşe
    noktalarından tek tek sürüklenerek boyutlandırılabilir.
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

        self.handles = []

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
    # Boyutlandırma Tutamaçları
    # -------------------------------------------------

    def _create_handles(self):

        self._remove_handles()

        for i in range(self.polygon().count()):

            handle = ROIVertexHandle(self, i)
            handle.setParentItem(self)
            handle.setPos(self.polygon().at(i))

            self.handles.append(handle)

    def _remove_handles(self):

        for handle in self.handles:

            handle.setParentItem(None)

            if handle.scene() is not None:
                handle.scene().removeItem(handle)

        self.handles = []

    def update_vertex(self, index: int, local_pos):

        polygon = self.polygon()

        points = [polygon.at(i) for i in range(polygon.count())]

        if index >= len(points):
            return

        points[index] = local_pos

        self.setPolygon(QPolygonF(points))

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

            if value:
                self._create_handles()
            else:
                self._remove_handles()

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
        set_channels(items: list[tuple[str, str | None]])
        get_selected_channel_id() -> str | None

    Controller'ın dinlediği sinyaller:

        save_button.clicked
        auto_detect_button.clicked
        channel_combo.currentIndexChanged
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
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # ---------- Kamera Kanalı Seçimi ----------
        # (Bandın tek kamerası varsa bu satır gizlenir - set_channels().)

        self.channel_container = QWidget()

        channel_row = QHBoxLayout(self.channel_container)
        channel_row.setContentsMargins(0, 0, 0, 0)

        channel_row.addWidget(QLabel("Düzenlenen Kamera:"))

        self.channel_combo = QComboBox()
        self.channel_combo.setToolTip(
            "Bu band birden fazla kameraya sahip. Hangi kameranın "
            "ROI'lerini düzenlediğinizi buradan seçin."
        )
        channel_row.addWidget(self.channel_combo, stretch=1)

        layout.addWidget(self.channel_container)

        self.channel_container.setVisible(False)

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
        self.view.setMinimumSize(400, 300)
        layout.addWidget(self.view)

        # ---------- Butonlar ----------

        button_row = QHBoxLayout()

        self.new_roi_button = QPushButton("Yeni ROI")
        self.new_roi_button.setCheckable(True)
        self.new_roi_button.clicked.connect(
            self.toggle_drawing_mode
        )
        button_row.addWidget(self.new_roi_button)

        self.auto_detect_button = QPushButton("Otomatik ROI Bul")
        button_row.addWidget(self.auto_detect_button)

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
        ).copy()

        # .copy() ZORUNLU: kopyalanmazsa QImage rgb'nin arabelleğini
        # sarmalar, bu fonksiyon dönünce rgb serbest kalabilir ve
        # ilk (gecikmeli/async) paint sırasında Qt geçersiz belleğe
        # erişip "access violation" ile çöker.

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
    # Kamera Kanalı Seçimi
    # -------------------------------------------------

    def set_channels(self, items: list):
        """
        items: [(etiket, channel_id_ya_da_None), ...]
        İlk eleman her zaman birincil kamerayı (channel_id=None)
        temsil etmeli. Sadece birincil varsa (tek eleman), seçim
        kutusu tek kameralı bandlarda kafa karıştırmasın diye
        tamamen gizlenir.
        """

        self.channel_combo.blockSignals(True)

        self.channel_combo.clear()

        for label, channel_id in items:
            self.channel_combo.addItem(label, channel_id)

        self.channel_combo.blockSignals(False)

        self.channel_container.setVisible(len(items) > 1)

    def get_selected_channel_id(self):

        return self.channel_combo.currentData()

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