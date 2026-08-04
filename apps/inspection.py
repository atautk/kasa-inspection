import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication, QDialog

from modules.ui.inspection.inspection_window import InspectionWindow
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

    window = InspectionWindow()
    window.setWindowTitle(f"KASA INSPECTION - {operator_name}")

    from modules.ui.inspection.inspection_ui_controller import InspectionUIController
    controller = InspectionUIController(
        window,
        root=ROOT,
        operator_name=operator_name
    )

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
