import sys
import subprocess
from pathlib import Path

APPS_DIR = Path(__file__).resolve().parent
ROOT = APPS_DIR.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton
)
from PySide6.QtCore import Qt

from modules.ui.window_utils import restore_or_center, save_geometry

SETTINGS_KEY = "launcher"


class LauncherWindow(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("KASA INSPECTION")

        restore_or_center(self, SETTINGS_KEY, 360, 220)

        layout = QVBoxLayout(self)

        title = QLabel("KASA INSPECTION SYSTEM")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        configurator_button = QPushButton("Configurator")
        configurator_button.setMinimumHeight(48)
        configurator_button.clicked.connect(self.launch_configurator)
        layout.addWidget(configurator_button)

        inspection_button = QPushButton("Inspection")
        inspection_button.setMinimumHeight(48)
        inspection_button.clicked.connect(self.launch_inspection)
        layout.addWidget(inspection_button)

    # -------------------------------------------------

    def launch_configurator(self):

        self._launch("configurator.py")

    def launch_inspection(self):

        self._launch("inspection.py")

    # -------------------------------------------------

    def _launch(self, script_name: str):

        subprocess.Popen(
            [sys.executable, str(APPS_DIR / script_name)]
        )

    # -------------------------------------------------

    def closeEvent(self, event):

        save_geometry(self, SETTINGS_KEY)

        super().closeEvent(event)


def main():

    app = QApplication(sys.argv)

    window = LauncherWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
