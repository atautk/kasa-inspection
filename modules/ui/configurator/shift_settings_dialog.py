from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QTimeEdit,
    QComboBox,
    QPushButton,
    QMessageBox
)
from PySide6.QtCore import Qt, QTime

from ..window_utils import restore_or_center, save_geometry

SETTINGS_KEY = "shift_settings_dialog"

UNASSIGNED_LABEL = "(Atanmamış)"


class ShiftSettingsDialog(QDialog):
    """
    Bir bandın vardiya pencerelerini (sabit saat aralıkları, ör.
    "Sabah" 07:30-15:30, isteğe bağlı bir operatör ataması ile)
    ekleme/düzenleme/silme penceresi. Üretim hedefi/tempo takibi YOK
    - sadece pencere içindeki üretim sayısı gösterilir (bkz.
    ShiftTrackingMixin) ve istatistiklerdeki vardiya bazlı NG trendi
    bu pencerelere göre gruplanır (bkz.
    InspectionLogger.compute_shift_trend). Hiç pencere yoksa vardiya
    takibi tamamen kapalıdır.
    """

    def __init__(self, band_manager, band, operator_manager=None, parent=None):

        super().__init__(parent)

        self.band_manager = band_manager
        self.band = band
        self.operator_manager = operator_manager

        self.setWindowTitle(f"Vardiya Ayarları - {band.name}")
        self.setModal(True)
        restore_or_center(self, SETTINGS_KEY, 480, 400)

        layout = QVBoxLayout(self)

        info_label = QLabel(
            "Vardiya pencereleri tanımlayın (ör. \"Sabah\" 07:30-15:30) "
            "ve isterseniz o vardiyada çalışan operatörü atayın. Hiç "
            "pencere yoksa vardiya takibi tamamen kapalı olur."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray;")
        layout.addWidget(info_label)

        self.shift_list = QListWidget()
        self.shift_list.itemDoubleClicked.connect(self._on_edit_clicked)
        layout.addWidget(self.shift_list)

        button_row = QHBoxLayout()

        self.add_button = QPushButton("&Ekle")
        self.add_button.clicked.connect(self._on_add_clicked)
        button_row.addWidget(self.add_button)

        self.edit_button = QPushButton("&Düzenle")
        self.edit_button.clicked.connect(self._on_edit_clicked)
        button_row.addWidget(self.edit_button)

        self.remove_button = QPushButton("&Sil")
        self.remove_button.clicked.connect(self._on_remove_clicked)
        button_row.addWidget(self.remove_button)

        button_row.addStretch()

        self.close_button = QPushButton("&Kapat")
        self.close_button.clicked.connect(self.accept)
        button_row.addWidget(self.close_button)

        layout.addLayout(button_row)

        self._reload_list()

    # -------------------------------------------------

    def closeEvent(self, event):
        save_geometry(self, SETTINGS_KEY)
        super().closeEvent(event)

    # -------------------------------------------------

    def _reload_list(self):

        self.shift_list.clear()

        for shift in self.band.shifts:

            text = f"{shift.name}  ({shift.start} - {shift.end})"

            if shift.operator:
                text += f"  — {shift.operator}"

            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, shift.id)
            self.shift_list.addItem(item)

    # -------------------------------------------------

    def _operator_names(self) -> list:

        if self.operator_manager is None:
            return []

        return self.operator_manager.list_operators()

    def _on_add_clicked(self):

        dialog = ShiftWindowEditDialog(
            self, operator_names=self._operator_names()
        )

        if dialog.exec() != QDialog.Accepted:
            return

        name, start, end, operator = dialog.get_values()

        self.band_manager.add_shift(self.band, name, start, end, operator)
        self._reload_list()

    def _on_edit_clicked(self):

        item = self.shift_list.currentItem()

        if item is None:
            QMessageBox.warning(
                self, "Uyarı", "Lütfen düzenlenecek bir vardiya seçin."
            )
            return

        shift_id = item.data(Qt.UserRole)

        shift = next(
            (s for s in self.band.shifts if s.id == shift_id), None
        )

        if shift is None:
            return

        dialog = ShiftWindowEditDialog(
            self,
            name=shift.name,
            start=shift.start,
            end=shift.end,
            operator=shift.operator,
            operator_names=self._operator_names()
        )

        if dialog.exec() != QDialog.Accepted:
            return

        name, start, end, operator = dialog.get_values()

        self.band_manager.update_shift(
            self.band, shift_id, name, start, end, operator
        )
        self._reload_list()

    def _on_remove_clicked(self):

        item = self.shift_list.currentItem()

        if item is None:
            QMessageBox.warning(
                self, "Uyarı", "Lütfen silinecek bir vardiya seçin."
            )
            return

        answer = QMessageBox.question(
            self, "Emin misiniz?",
            "Bu vardiya penceresi silinecek. Devam edilsin mi?"
        )

        if answer != QMessageBox.Yes:
            return

        self.band_manager.remove_shift(self.band, item.data(Qt.UserRole))
        self._reload_list()


class ShiftWindowEditDialog(QDialog):
    """
    Tek bir vardiya penceresinin ad/başlangıç/bitiş saatini ve
    (isteğe bağlı) atanan operatörünü düzenler.
    """

    def __init__(
        self,
        parent=None,
        name="",
        start="08:00",
        end="16:00",
        operator="",
        operator_names=None
    ):

        super().__init__(parent)

        self.setWindowTitle("Vardiya Penceresi")
        self.setModal(True)

        layout = QVBoxLayout(self)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Vardiya Adı:"))
        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("ör. Sabah, Öğle, Gece")
        name_row.addWidget(self.name_edit, stretch=1)
        layout.addLayout(name_row)

        start_row = QHBoxLayout()
        start_row.addWidget(QLabel("Başlangıç:"))
        self.start_edit = QTimeEdit()
        self.start_edit.setDisplayFormat("HH:mm")
        self.start_edit.setTime(
            QTime.fromString(start, "HH:mm")
        )
        start_row.addWidget(self.start_edit, stretch=1)
        layout.addLayout(start_row)

        end_row = QHBoxLayout()
        end_row.addWidget(QLabel("Bitiş:"))
        self.end_edit = QTimeEdit()
        self.end_edit.setDisplayFormat("HH:mm")
        self.end_edit.setTime(
            QTime.fromString(end, "HH:mm")
        )
        end_row.addWidget(self.end_edit, stretch=1)
        layout.addLayout(end_row)

        operator_row = QHBoxLayout()
        operator_row.addWidget(QLabel("Operatör:"))
        self.operator_combo = QComboBox()
        self.operator_combo.addItem(UNASSIGNED_LABEL, "")

        for operator_name in (operator_names or []):
            self.operator_combo.addItem(operator_name, operator_name)

        if operator:

            index = self.operator_combo.findData(operator)

            if index == -1:
                # Vardiyaya atanan operatör silinmiş/değişmiş olabilir -
                # listede yoksa yine de kaybolmasın diye ekle.
                self.operator_combo.addItem(operator, operator)
                index = self.operator_combo.count() - 1

            self.operator_combo.setCurrentIndex(index)

        operator_row.addWidget(self.operator_combo, stretch=1)
        layout.addLayout(operator_row)

        button_row = QHBoxLayout()
        button_row.addStretch()
        self.cancel_button = QPushButton("İptal")
        self.cancel_button.clicked.connect(self.reject)
        button_row.addWidget(self.cancel_button)
        self.save_button = QPushButton("&Tamam")
        self.save_button.clicked.connect(self._on_accept)
        button_row.addWidget(self.save_button)
        layout.addLayout(button_row)

    def _on_accept(self):

        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Uyarı", "Vardiya adı boş olamaz.")
            return

        self.accept()

    def get_values(self):

        return (
            self.name_edit.text().strip(),
            self.start_edit.time().toString("HH:mm"),
            self.end_edit.time().toString("HH:mm"),
            self.operator_combo.currentData()
        )
