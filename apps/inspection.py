import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication

from modules.ui.inspection.inspection_window import InspectionWindow


def main():

    app = QApplication(sys.argv)

    window = InspectionWindow()

    from modules.ui.inspection.inspection_ui_controller import InspectionUIController
    controller = InspectionUIController(window)

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
