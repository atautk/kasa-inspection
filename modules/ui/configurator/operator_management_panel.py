from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QMessageBox
)


class OperatorManagementPanel(QWidget):
    """
    Operatörleri listeler; onay bekleyen operatörleri onaylama ve
    operatör silme burada yapılır. Bu paneli kimin görebileceği
    (yönetici kontrolü) çağıran taraftan (ConfiguratorController)
    yapılır. Ayarlar penceresi içine gömülür - bkz. SettingsDialog.
    """

    COLUMNS = ["Ad", "Rol", "Durum"]

    def __init__(self, operator_manager, parent=None):

        super().__init__(parent)

        self.operator_manager = operator_manager

        layout = QVBoxLayout(self)

        title = QLabel("Operatörleri Yönet")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

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

        layout.addLayout(button_row)

        self.reload()

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
