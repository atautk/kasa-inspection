from pathlib import Path

from PySide6.QtCore import QSettings

ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PATH = ROOT / "window_settings.ini"

SCALE_OPTIONS = {
    "Normal": 1.0,
    "Büyük": 1.2,
    "Çok Büyük": 1.4
}

BASE_FONT_POINT_SIZE = 9

# Standart OK/NG renkleri (RGB).
STANDARD_OK_RGB = (0, 170, 0)
STANDARD_NG_RGB = (200, 0, 0)

# Yüksek kontrast / renk körü dostu mod: kırmızı/yeşil ayrımını
# yapamayan kullanıcılar (en yaygın renk körlüğü türleri) için
# mavi/turuncu, Okabe-Ito paletine dayanır.
HIGH_CONTRAST_OK_RGB = (0, 114, 178)
HIGH_CONTRAST_NG_RGB = (230, 159, 0)


def _settings() -> QSettings:

    return QSettings(str(SETTINGS_PATH), QSettings.IniFormat)


# -------------------------------------------------
# Yazı / Arayüz Ölçeği
# -------------------------------------------------

def get_ui_scale() -> float:

    return float(
        _settings().value("accessibility/ui_scale", 1.0, type=float)
    )


def set_ui_scale(scale: float):

    settings = _settings()
    settings.setValue("accessibility/ui_scale", scale)

    # _settings() her çağrıda yeni bir QSettings nesnesi döndürüyor;
    # sync() olmadan bu yazma, aynı oturumda hemen ardından yapılan
    # bir get_ui_scale() çağrısına yansımayabiliyordu (ör. "Kaydet ve
    # Uygula" akışında set() sonrası apply_ui_scale() içindeki get()
    # eski değeri okuyordu).
    settings.sync()


def apply_ui_scale(app):
    """
    Çalışan QApplication'a mevcut yazı ölçeğini uygular. Zaten
    oluşturulmuş çoğu widget, kendi fontunu ayrıca ayarlamadığı
    sürece bu değişikliği anında yansıtır (Qt'nin standart
    application-font-change davranışı).
    """

    scale = get_ui_scale()

    font = app.font()
    font.setPointSizeF(BASE_FONT_POINT_SIZE * scale)

    app.setFont(font)


# -------------------------------------------------
# Yüksek Kontrast / Renk Körü Dostu Mod
# -------------------------------------------------

def is_high_contrast() -> bool:

    return bool(
        _settings().value(
            "accessibility/high_contrast", False, type=bool
        )
    )


def set_high_contrast(enabled: bool):

    settings = _settings()
    settings.setValue("accessibility/high_contrast", enabled)
    settings.sync()


def get_ok_color_rgb() -> tuple:

    return HIGH_CONTRAST_OK_RGB if is_high_contrast() else STANDARD_OK_RGB


def get_ng_color_rgb() -> tuple:

    return HIGH_CONTRAST_NG_RGB if is_high_contrast() else STANDARD_NG_RGB


def get_ok_color_bgr() -> tuple:

    r, g, b = get_ok_color_rgb()

    return (b, g, r)


def get_ng_color_bgr() -> tuple:

    r, g, b = get_ng_color_rgb()

    return (b, g, r)


def _lighten(rgb: tuple, factor: float = 0.72) -> tuple:

    r, g, b = rgb

    return (
        int(r + (255 - r) * factor),
        int(g + (255 - g) * factor),
        int(b + (255 - b) * factor)
    )


def get_ok_color_light_rgb() -> tuple:

    return _lighten(get_ok_color_rgb())


def get_ng_color_light_rgb() -> tuple:

    return _lighten(get_ng_color_rgb())
