from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtCore import Qt, QRectF

from modules.utils import accessibility_settings as a11y


class TrendChartWidget(QWidget):
    """
    Günlük NG oranını (%) basit bir çubuk grafik olarak çizer.
    Ekstra bir grafik kütüphanesi gerektirmez, QPainter ile çizilir.
    """

    MARGIN_LEFT = 45
    MARGIN_RIGHT = 20
    MARGIN_TOP = 20
    MARGIN_BOTTOM = 35

    def __init__(self, parent=None):

        super().__init__(parent)

        self.data = []

        self.setMinimumHeight(220)
        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )

    # -------------------------------------------------

    def set_data(self, data: list):

        self.data = data

        self.update()

    # -------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()

        painter.fillRect(rect, QColor(255, 255, 255))

        if not self.data:

            painter.setPen(QColor(120, 120, 120))
            painter.drawText(rect, Qt.AlignCenter, "Veri yok")
            painter.end()
            return

        chart_rect = QRectF(
            self.MARGIN_LEFT,
            self.MARGIN_TOP,
            rect.width() - self.MARGIN_LEFT - self.MARGIN_RIGHT,
            rect.height() - self.MARGIN_TOP - self.MARGIN_BOTTOM
        )

        self._draw_grid(painter, chart_rect)
        self._draw_bars(painter, chart_rect)
        self._draw_axes(painter, chart_rect)

        painter.end()

    # -------------------------------------------------

    def _draw_grid(self, painter, chart_rect):

        for i in range(5):

            y = chart_rect.bottom() - chart_rect.height() * (i / 4)

            painter.setPen(QPen(QColor(225, 225, 225), 1))
            painter.drawLine(
                chart_rect.left(), y,
                chart_rect.right(), y
            )

            painter.setPen(QColor(110, 110, 110))
            painter.drawText(
                QRectF(0, y - 10, self.MARGIN_LEFT - 6, 20),
                Qt.AlignRight | Qt.AlignVCenter,
                f"%{int(i / 4 * 100)}"
            )

    # -------------------------------------------------

    def _draw_bars(self, painter, chart_rect):

        n = len(self.data)

        slot_width = chart_rect.width() / n
        bar_width = slot_width * 0.6

        label_step = max(1, n // 12)

        for index, entry in enumerate(self.data):

            x_center = chart_rect.left() + slot_width * index + slot_width / 2

            ratio = min(max(entry["ng_ratio"], 0.0), 100.0)

            bar_height = chart_rect.height() * (ratio / 100.0)

            bar_rect = QRectF(
                x_center - bar_width / 2,
                chart_rect.bottom() - bar_height,
                bar_width,
                bar_height
            )

            color = QColor(
                *(
                    a11y.get_ok_color_rgb()
                    if ratio == 0
                    else a11y.get_ng_color_rgb()
                )
            )

            painter.fillRect(bar_rect, color)

            if index % label_step == 0 or index == n - 1:

                painter.setPen(QColor(90, 90, 90))

                painter.drawText(
                    QRectF(
                        x_center - slot_width / 2,
                        chart_rect.bottom() + 4,
                        slot_width,
                        self.MARGIN_BOTTOM - 4
                    ),
                    Qt.AlignCenter,
                    entry["date"][5:]
                )

    # -------------------------------------------------

    def _draw_axes(self, painter, chart_rect):

        painter.setPen(QPen(QColor(90, 90, 90), 1))

        painter.drawLine(
            chart_rect.bottomLeft(),
            chart_rect.bottomRight()
        )

        painter.drawLine(
            chart_rect.topLeft(),
            chart_rect.bottomLeft()
        )
