from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtCore import Qt, QRectF

from modules.utils import accessibility_settings as a11y


class HorizontalBarChartWidget(QWidget):
    """
    Kategori (model/ROI) başına NG oranını (%) yatay çubuklarla
    gösterir. Uzun etiketler için tablo yerine hızlı görsel
    karşılaştırma sağlar.

    set_data([{"label": str, "ok": int, "ng": int}, ...])
    """

    MARGIN_LEFT = 120
    MARGIN_RIGHT = 60
    MARGIN_TOP = 6
    MARGIN_BOTTOM = 6
    ROW_HEIGHT = 26

    def __init__(self, parent=None):

        super().__init__(parent)

        self.data = []

        self.setMinimumHeight(80)
        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Minimum
        )

    # -------------------------------------------------

    def set_data(self, data: list):

        self.data = data

        self.setMinimumHeight(
            max(
                80,
                len(data) * self.ROW_HEIGHT
                + self.MARGIN_TOP + self.MARGIN_BOTTOM
            )
        )

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

        chart_width = max(
            rect.width() - self.MARGIN_LEFT - self.MARGIN_RIGHT,
            10
        )

        ok_color = QColor(*a11y.get_ok_color_rgb())
        ng_color = QColor(*a11y.get_ng_color_rgb())

        for index, entry in enumerate(self.data):

            y = self.MARGIN_TOP + index * self.ROW_HEIGHT

            ok = entry.get("ok", 0)
            ng = entry.get("ng", 0)
            total = ok + ng

            ratio = (ng / total * 100) if total else 0.0

            bar_width = chart_width * (ratio / 100.0)

            color = ng_color if ratio > 0 else ok_color

            painter.setPen(QPen(QColor(225, 225, 225), 1))
            painter.drawRect(
                QRectF(
                    self.MARGIN_LEFT, y + 4,
                    chart_width, self.ROW_HEIGHT - 10
                )
            )

            if bar_width > 0:

                painter.fillRect(
                    QRectF(
                        self.MARGIN_LEFT, y + 4,
                        bar_width, self.ROW_HEIGHT - 10
                    ),
                    color
                )

            painter.setPen(QColor(60, 60, 60))
            painter.drawText(
                QRectF(
                    0, y, self.MARGIN_LEFT - 8, self.ROW_HEIGHT
                ),
                Qt.AlignRight | Qt.AlignVCenter,
                entry["label"]
            )

            painter.drawText(
                QRectF(
                    self.MARGIN_LEFT + chart_width + 6, y,
                    self.MARGIN_RIGHT - 6, self.ROW_HEIGHT
                ),
                Qt.AlignLeft | Qt.AlignVCenter,
                f"%{ratio:.1f}"
            )

        painter.end()
