from PySide6.QtCore import QSettings
from PySide6.QtGui import QGuiApplication

from modules.utils.paths import get_app_root

ROOT = get_app_root()

SETTINGS_PATH = ROOT / "window_settings.ini"


def size_and_center(window, width: int, height: int):
    """
    Pencereyi ekran boyutuna göre sınırlayıp ortalar.

    Sabit resize() çağrıları küçük ekranlarda pencereyi taşırıp
    kenarlardan kesebiliyor ya da varsayılan konumda (genelde
    sol üst köşe) tuhaf görünebiliyordu.
    """

    screen = QGuiApplication.primaryScreen()

    if screen is None:

        window.resize(width, height)
        return

    available = screen.availableGeometry()

    width = min(width, int(available.width() * 0.95))
    height = min(height, int(available.height() * 0.95))

    window.resize(width, height)

    x = available.x() + (available.width() - width) // 2
    y = available.y() + (available.height() - height) // 2

    window.move(x, y)


def get_app_settings() -> QSettings:
    """
    Pencere boyutu/konumu gibi makineye özel ayarların hepsinin
    saklandığı ortak QSettings nesnesi. Başka modüller (ör. son
    kullanılan band/model bilgisini saklayan inspection oturum
    durumu) de aynı dosyayı, kendi anahtar öneki altında kullanabilir.
    """

    return QSettings(str(SETTINGS_PATH), QSettings.IniFormat)


def restore_or_center(
    window,
    key: str,
    default_width: int,
    default_height: int
):
    """
    Daha önce kaydedilmiş pencere boyutu/konumu varsa onu geri
    yükler, yoksa ekrana göre ortalanmış varsayılan boyutu kullanır.
    """

    settings = get_app_settings()

    geometry = settings.value(f"{key}/geometry")

    if geometry is not None:

        window.restoreGeometry(geometry)

    else:

        size_and_center(window, default_width, default_height)


def save_geometry(window, key: str):

    settings = get_app_settings()

    settings.setValue(f"{key}/geometry", window.saveGeometry())
