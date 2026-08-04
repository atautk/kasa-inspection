from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QInputDialog
)
from PySide6.QtCore import Qt

from modules.utils.logger import get_logger

app_logger = get_logger()


class LoginDialog(QDialog):
    """
    Uygulama açılışında operatör kimliğini doğrular.

    Başarılı girişte `authenticated_operator` alanı operatörün
    adını tutar, dialog QDialog.Accepted ile kapanır.
    """

    def __init__(self, operator_manager, parent=None):

        super().__init__(parent)

        self.operator_manager = operator_manager
        self.authenticated_operator = None

        self.setWindowTitle("Giriş")
        self.setModal(True)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Operatör:"))

        self.operator_combo = QComboBox()
        self.operator_combo.addItems(
            self.operator_manager.list_operators()
        )
        layout.addWidget(self.operator_combo)

        layout.addWidget(QLabel("PIN:"))

        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.returnPressed.connect(self._on_login_clicked)
        layout.addWidget(self.pin_input)

        button_row = QHBoxLayout()

        self.login_button = QPushButton("&Giriş Yap")
        self.login_button.setDefault(True)
        self.login_button.clicked.connect(self._on_login_clicked)
        button_row.addWidget(self.login_button)

        self.add_operator_button = QPushButton("&Yeni Operatör Ekle")
        self.add_operator_button.clicked.connect(
            self._on_add_operator_clicked
        )
        button_row.addWidget(self.add_operator_button)

        layout.addLayout(button_row)

    # -------------------------------------------------

    def _on_login_clicked(self):

        name = self.operator_combo.currentText()
        pin = self.pin_input.text()

        if not name:

            QMessageBox.warning(
                self,
                "Uyarı",
                "Kayıtlı operatör bulunamadı."
            )

            return

        if not self.operator_manager.verify(name, pin):

            QMessageBox.warning(
                self,
                "Hata",
                "PIN hatalı."
            )

            self.pin_input.clear()

            return

        if not self.operator_manager.is_approved(name):

            QMessageBox.warning(
                self,
                "Onay Bekliyor",
                f"'{name}' hesabı henüz yönetici onayı bekliyor. "
                "Onaylanmadan giriş yapılamaz."
            )

            self.pin_input.clear()

            return

        self.authenticated_operator = name

        app_logger.info("[%s] giriş yaptı", name)

        self.accept()

    # -------------------------------------------------

    def _on_add_operator_clicked(self):

        name, ok = QInputDialog.getText(
            self,
            "Yeni Operatör",
            "Operatör Adı"
        )

        if not ok:
            return

        name = name.strip()

        if name == "":
            return

        pin, ok = QInputDialog.getText(
            self,
            "Yeni Operatör",
            f"{name} için PIN belirleyin",
            QLineEdit.Password
        )

        if not ok or pin == "":
            return

        try:

            self.operator_manager.create_operator(name, pin)

        except ValueError as e:

            QMessageBox.warning(self, "Hata", str(e))

            return

        self.operator_combo.blockSignals(True)
        self.operator_combo.clear()
        self.operator_combo.addItems(
            self.operator_manager.list_operators()
        )
        self.operator_combo.setCurrentText(name)
        self.operator_combo.blockSignals(False)

        QMessageBox.information(
            self,
            "Başarılı",
            f"{name} operatör olarak eklendi. Giriş yapabilmesi için "
            "bir yöneticinin onaylaması gerekiyor."
        )
