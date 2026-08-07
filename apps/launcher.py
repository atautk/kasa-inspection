import sys
import subprocess
from pathlib import Path

APPS_DIR = Path(__file__).resolve().parent

# python ile doğrudan çalıştırıldığında "modules" paketinin
# bulunabilmesi için proje kökü sys.path'e eklenir - PyInstaller ile
# paketlenmiş halde bu satır etkisizdir (import'lar zaten bundle
# içinden çözülür), o yüzden burada __file__ tabanlı yol kullanmak
# güvenlidir.
sys.path.insert(0, str(APPS_DIR.parent))

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from modules.ui.window_utils import restore_or_center, save_geometry
from modules.utils import accessibility_settings as a11y
from modules.utils.paths import get_resource_path

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

        self._launch("configurator.py", "Configurator")

    def launch_inspection(self):

        self._launch("inspection.py", "Inspection")

    # -------------------------------------------------

    def _launch(self, script_name: str, app_name: str):
        """
        Geliştirme ortamında (python ile) ilgili script'i aynı
        yorumlayıcıyla ayrı bir process olarak açar. PyInstaller ile
        paketlenmiş halde ise sys.executable Launcher.exe'nin
        kendisidir ve script_name diskte bir .py dosyası olarak
        bulunmaz - onun yerine build_exe.py'nin ürettiği kardeş
        <UygulamaAdı>/<UygulamaAdı>.exe açılır (bkz.
        modules/utils/paths.get_app_root - aynı paylaşılan üst
        klasörün altındadırlar).
        """

        if getattr(sys, "frozen", False):

            exe_path = (
                Path(sys.executable).resolve().parent.parent
                / app_name / f"{app_name}.exe"
            )

            subprocess.Popen([str(exe_path)])
            return

        subprocess.Popen(
            [sys.executable, str(APPS_DIR / script_name)]
        )

    # -------------------------------------------------

    def closeEvent(self, event):

        save_geometry(self, SETTINGS_KEY)

        super().closeEvent(event)


def main():

    app = QApplication(sys.argv)

    a11y.apply_ui_scale(app)

    icon_path = get_resource_path("assets/icon.png")

    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = LauncherWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
