from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QMessageBox
)

from ..window_utils import restore_or_center, save_geometry

SETTINGS_KEY = "operator_management_dialog"


class OperatorManagementDialog(QDialog):
    """
    Operatörleri listeler; onay bekleyen operatörleri onaylama ve
    operatör silme burada yapılır. Bu pencereyi kimin açabileceği
    (yönetici kontrolü) çağıran taraftan (ConfiguratorController)
    yapılır.
    """

    COLUMNS = ["Ad", "Rol", "Durum"]

    def __init__(self, operator_manager, parent=None):

        super().__init__(parent)

        self.operator_manager = operator_manager

        self.setWindowTitle("Operatörleri Yönet")
        restore_or_center(self, SETTINGS_KEY, 480, 360)

        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table)

        button_row = QHBoxLayout()

        self.approve_button = QPushButton("Onayla")
        self.approve_button.clicked.connect(self._on_approve_clicked)
        button_row.addWidget(self.approve_button)

        self.delete_button = QPushButton("Sil")
        self.delete_button.clicked.connect(self._on_delete_clicked)
        button_row.addWidget(self.delete_button)

        button_row.addStretch()

        self.close_button = QPushButton("Kapat")
        self.close_button.clicked.connect(self.close)
        button_row.addWidget(self.close_button)

        layout.addLayout(button_row)

        self.reload()

    # -------------------------------------------------

    def closeEvent(self, event):

        save_geometry(self, SETTINGS_KEY)

        super().closeEvent(event)

    # -------------------------------------------------
    # Liste
    # -------------------------------------------------

    def reload(self):

        operators = self.operator_manager.list_operator_details()

        self.table.setRowCount(len(operators))

        for row, operator in enumerate(operators):

            status = "Onaylı" if operator.approved else "Onay Bekliyor"

            values = [operator.name, operator.role, status]

            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))

    def _selected_name(self):

        row = self.table.currentRow()

        if row < 0:
            return None

        item = self.table.item(row, 0)

        return item.text() if item else None

    # -------------------------------------------------
    # İşlemler
    # -------------------------------------------------

    def _on_approve_clicked(self):

        name = self._selected_name()

        if name is None:

            QMessageBox.information(
                self,
                "Bilgi",
                "Önce bir operatör seçin."
            )

            return

        self.operator_manager.approve_operator(name)

        self.reload()

    def _on_delete_clicked(self):

        name = self._selected_name()

        if name is None:

            QMessageBox.information(
                self,
                "Bilgi",
                "Önce bir operatör seçin."
            )

            return

        confirm = QMessageBox.question(
            self,
            "Onay",
            f"'{name}' operatörünü silmek istediğinize emin misiniz?"
        )

        if confirm != QMessageBox.Yes:
            return

        try:

            self.operator_manager.delete_operator(name)

        except ValueError as e:

            QMessageBox.warning(self, "Hata", str(e))

            return

        self.reload()
