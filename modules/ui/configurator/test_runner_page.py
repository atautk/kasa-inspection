from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTextEdit,
    QSplitter
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt


class TestRunnerPage(QWidget):
    """
    Test Çalıştırma sekmesi.

    Bu sınıf SADECE UI'dan sorumludur; pytest'i nasıl çalıştıracağını
    veya sonuçları nasıl ayrıştıracağını bilmez, bunu Controller yapar.

    Controller'ın kullandığı public metodlar:

        set_running(running: bool)
        set_summary(text: str)
        set_results(results: list[dict])  # {name, status, duration, message}
        clear_results()

    Controller'ın dinlediği sinyal:

        run_button.clicked
    """

    COLUMNS = ["Test", "Durum", "Süre (sn)"]

    STATUS_LABELS = {
        "passed": "✓ Başarılı",
        "failed": "✗ Başarısız",
        "error": "‼ Hata",
        "skipped": "– Atlandı"
    }

    PASS_COLOR = QColor(200, 255, 200)
    FAIL_COLOR = QColor(255, 200, 200)
    SKIP_COLOR = QColor(255, 240, 200)

    def __init__(self):

        super().__init__()

        self._results = []

        layout = QVBoxLayout(self)

        top_row = QHBoxLayout()

        self.run_button = QPushButton("Testleri Çalıştır")
        top_row.addWidget(self.run_button)

        self.summary_label = QLabel("Henüz çalıştırılmadı.")
        top_row.addWidget(self.summary_label, stretch=1)

        layout.addLayout(top_row)

        splitter = QSplitter(Qt.Vertical)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(len(self.COLUMNS))
        self.results_table.setHorizontalHeaderLabels(self.COLUMNS)
        self.results_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.itemSelectionChanged.connect(
            self._on_selection_changed
        )
        splitter.addWidget(self.results_table)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setPlaceholderText(
            "Ayrıntıları görmek için bir test satırına tıklayın."
        )
        splitter.addWidget(self.detail_text)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, stretch=1)

    # -------------------------------------------------
    # Durum
    # -------------------------------------------------

    def set_running(self, running: bool):

        self.run_button.setEnabled(not running)

        self.run_button.setText(
            "Çalışıyor..." if running else "Testleri Çalıştır"
        )

    def set_summary(self, text: str):

        self.summary_label.setText(text)

    # -------------------------------------------------
    # Sonuçlar
    # -------------------------------------------------

    def set_results(self, results: list):

        self._results = results

        self.results_table.setRowCount(len(results))

        for row, result in enumerate(results):

            status = result.get("status", "?")

            text = self.STATUS_LABELS.get(status, status)
            color = None

            if status == "passed":
                color = self.PASS_COLOR
            elif status in ("failed", "error"):
                color = self.FAIL_COLOR
            elif status == "skipped":
                color = self.SKIP_COLOR

            values = [
                result.get("name", ""),
                text,
                f"{result.get('duration', 0):.3f}"
            ]

            for column, value in enumerate(values):

                item = QTableWidgetItem(value)

                if color is not None:
                    item.setBackground(color)

                self.results_table.setItem(row, column, item)

        self.detail_text.clear()

    def clear_results(self):

        self.results_table.setRowCount(0)
        self._results = []

        self.detail_text.clear()

    # -------------------------------------------------

    def _on_selection_changed(self):

        row = self.results_table.currentRow()

        if row < 0 or row >= len(self._results):

            self.detail_text.clear()
            return

        message = self._results[row].get("message", "")

        self.detail_text.setPlainText(message or "(ayrıntı yok)")
