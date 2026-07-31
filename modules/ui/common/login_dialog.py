from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QLineEdit,
    QPushButton,
    QMessageBox
)
from PySide6.QtCore import Qt


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

        self.login_button = QPushButton("Giriş Yap")
        self.login_button.clicked.connect(self._on_login_clicked)
        button_row.addWidget(self.login_button)

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

        if self.operator_manager.verify(name, pin):

            self.authenticated_operator = name

            self.accept()

        else:

            QMessageBox.warning(
                self,
                "Hata",
                "PIN hatalı."
            )

            self.pin_input.clear()
