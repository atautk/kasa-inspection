from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QCheckBox,
    QPushButton,
    QApplication
)

from modules.utils import accessibility_settings as a11y


class AccessibilityDialog(QDialog):
    """
    Erişebilirlik Ayarları: yazı/arayüz boyutu ve yüksek kontrast
    (renk körü dostu) mod buradan ayarlanır.

    Yazı boyutu kaydedilince çalışan uygulamaya hemen uygulanır.
    Renk ayarı ise OK/NG gösterilen her yerde (canlı kamera görüntüsü,
    sonuç tablosu, NG uyarısı, trend grafiği) bir sonraki güncellemede
    otomatik yansır - yeniden başlatmaya gerek yoktur.
    """

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setWindowTitle("Erişebilirlik Ayarları")
        self.setModal(True)

        layout = QVBoxLayout(self)

        scale_row = QHBoxLayout()

        scale_row.addWidget(QLabel("Yazı / Arayüz Boyutu:"))

        self.scale_combo = QComboBox()
        self.scale_combo.addItems(list(a11y.SCALE_OPTIONS.keys()))
        scale_row.addWidget(self.scale_combo)

        layout.addLayout(scale_row)

        self.high_contrast_checkbox = QCheckBox(
            "Yüksek Kontrast / Renk Körü Dostu Mod "
            "(OK = mavi, NG = turuncu)"
        )
        layout.addWidget(self.high_contrast_checkbox)

        info_label = QLabel(
            "Not: OK/NG durumu her zaman ayrıca yazıyla da "
            "gösterilir; bu ayar sadece renkleri değiştirir."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray;")
        layout.addWidget(info_label)

        button_row = QHBoxLayout()

        self.save_button = QPushButton("&Kaydet ve Uygula")
        self.save_button.clicked.connect(self._on_save_clicked)
        button_row.addWidget(self.save_button)

        self.close_button = QPushButton("&Kapat")
        self.close_button.clicked.connect(self.reject)
        button_row.addWidget(self.close_button)

        layout.addLayout(button_row)

        self._load_current_settings()

    # -------------------------------------------------

    def _load_current_settings(self):

        current_scale = a11y.get_ui_scale()

        for label, value in a11y.SCALE_OPTIONS.items():

            if abs(value - current_scale) < 0.001:

                self.scale_combo.setCurrentText(label)
                break

        self.high_contrast_checkbox.setChecked(a11y.is_high_contrast())

    # -------------------------------------------------

    def _on_save_clicked(self):

        label = self.scale_combo.currentText()
        scale = a11y.SCALE_OPTIONS.get(label, 1.0)

        a11y.set_ui_scale(scale)
        a11y.set_high_contrast(self.high_contrast_checkbox.isChecked())

        app = QApplication.instance()

        if app is not None:
            a11y.apply_ui_scale(app)

        self.accept()
