from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLabel
)
from PySide6.QtCore import Qt


class ModelPage(QWidget):
    """
    Model Editor sekmesi.

    Bu sınıf SADECE UI'dan sorumludur. Dosya okuma/yazma
    (models/*.json) işini bilmez, bunu Controller yapar.

    Bir "Model" = isim (Clio, Duster, ...) + hangi ROI'lerin
    DOLU (FULL) olması gerektiği. Listede olmayan her ROI
    otomatik olarak BOŞ (EMPTY) kabul edilir.

    Controller'ın kullandığı public metodlar:

        set_models(models: list[dict])
        get_selected_model_id() -> str | None
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
            QLabel("Beklenen Durum (İşaretli = DOLU)")
        )

        self.roi_checklist = QListWidget()
        right_column.addWidget(self.roi_checklist)

        self.status_label = QLabel("-")
        right_column.addWidget(self.status_label)

        self.save_button = QPushButton("Kaydet")
        right_column.addWidget(self.save_button)

        layout.addLayout(right_column, 1)

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
    # Beklenen Durum (ROI Checklist)
    # -------------------------------------------------

    def set_roi_checklist(self, roi_names: list, checked_names: list):

        checked_set = set(checked_names)

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

    def get_checked_rois(self) -> list:

        checked = []

        for i in range(self.roi_checklist.count()):

            item = self.roi_checklist.item(i)

            if item.checkState() == Qt.Checked:

                checked.append(item.text())

        return checked

    def clear_roi_checklist(self):

        self.roi_checklist.clear()

    # -------------------------------------------------
    # Yardımcı
    # -------------------------------------------------

    def set_status(self, text: str):

        self.status_label.setText(text)