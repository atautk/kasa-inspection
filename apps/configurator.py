import sys
from pathlib import Path

# python ile doğrudan çalıştırıldığında "modules" paketinin
# bulunabilmesi için proje kökü sys.path'e eklenir - PyInstaller ile
# paketlenmiş halde bu satır etkisizdir (import'lar zaten bundle
# içinden çözülür), o yüzden burada __file__ tabanlı yol kullanmak
# güvenlidir.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtGui import QIcon

from modules.ui.configurator.main_window import MainWindow
from modules.ui.common.login_dialog import LoginDialog
from modules.configuration.operator_manager import OperatorManager
from modules.utils import accessibility_settings as a11y
from modules.utils.paths import get_app_root, get_resource_path
from modules.utils.theme import apply_light_theme

# Kalıcı veriler (band konfigürasyonları, operatör listesi) için kök
# dizin - paketlenmiş .exe'de proje kaynak koduyla değil, .exe'nin
# yanındaki paylaşılan klasörle eşleşir (bkz. modules/utils/paths.py).
ROOT = get_app_root()


def main():

    app = QApplication(sys.argv)

    apply_light_theme(app)
    a11y.apply_ui_scale(app)

    icon_path = get_resource_path("assets/icon.png")

    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    operator_manager = OperatorManager(
        ROOT / "configuration" / "operators.json"
    )

    login = LoginDialog(operator_manager)

    if login.exec() != QDialog.Accepted:
        sys.exit(0)

    operator_name = login.authenticated_operator

    window = MainWindow()
    window.setWindowTitle(f"KASA KURULUM - {operator_name}")

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
