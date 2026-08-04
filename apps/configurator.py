import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication, QDialog

from modules.ui.configurator.main_window import MainWindow
from modules.ui.common.login_dialog import LoginDialog
from modules.configuration.operator_manager import OperatorManager
from modules.utils import accessibility_settings as a11y


def main():

    app = QApplication(sys.argv)

    a11y.apply_ui_scale(app)

    operator_manager = OperatorManager(
        ROOT / "configuration" / "operators.json"
    )

    login = LoginDialog(operator_manager)

    if login.exec() != QDialog.Accepted:
        sys.exit(0)

    operator_name = login.authenticated_operator

    window = MainWindow()
    window.setWindowTitle(f"KASA CONFIGURATOR - {operator_name}")

    from modules.ui.configurator.configurator_controller import ConfiguratorController
    controller = ConfiguratorController(
        window,
        operator_name=operator_name,
        operator_manager=operator_manager
    )

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
