from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtGui import QPainter, QColor, QPen, QBrush
from PySide6.QtCore import Qt, QRectF


class PieChartWidget(QWidget):
    """
    Basit pasta grafiği + gösterge (legend). Ekstra bir grafik
    kütüphanesi gerektirmez, QPainter ile çizilir.

    set_data([{"label": str, "value": float, "color": QColor}, ...])
    """

    LEGEND_WIDTH = 150

    def __init__(self, parent=None):

        super().__init__(parent)

        self.slices = []

        self.setMinimumSize(260, 200)
        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )

    # -------------------------------------------------

    def set_data(self, slices: list):

        self.slices = slices

        self.update()

    # -------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()

        painter.fillRect(rect, QColor(255, 255, 255))

        total = sum(s["value"] for s in self.slices)

        if not self.slices or total <= 0:

            painter.setPen(QColor(120, 120, 120))
            painter.drawText(rect, Qt.AlignCenter, "Veri yok")
            painter.end()
            return

        chart_size = min(
            rect.width() - self.LEGEND_WIDTH,
            rect.height()
        ) - 20

        chart_size = max(chart_size, 40)

        chart_rect = QRectF(
            10,
            (rect.height() - chart_size) / 2,
            chart_size,
            chart_size
        )

        start_angle = 90 * 16

        for entry in self.slices:

            span = -round(entry["value"] / total * 360 * 16)

            painter.setBrush(QBrush(entry["color"]))
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.drawPie(chart_rect, start_angle, span)

            start_angle += span

        legend_x = chart_rect.right() + 20
        legend_y = rect.top() + 20

        for entry in self.slices:

            painter.setBrush(QBrush(entry["color"]))
            painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(legend_x, legend_y, 14, 14))

            percent = entry["value"] / total * 100

            painter.setPen(QColor(50, 50, 50))
            painter.drawText(
                QRectF(
                    legend_x + 20,
                    legend_y - 3,
                    self.LEGEND_WIDTH - 20,
                    20
                ),
                Qt.AlignLeft | Qt.AlignVCenter,
                f"{entry['label']}: {int(entry['value'])} "
                f"(%{percent:.1f})"
            )

            legend_y += 24

        painter.end()
