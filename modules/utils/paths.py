import sys
from pathlib import Path


def get_app_root() -> Path:
    """
    Uygulamanın kalıcı verilerinin (configuration/, logs/,
    window_settings.ini) bulunması gereken kök dizin.

    Normal (python ile) çalışırken bu proje köküdür. PyInstaller ile
    paketlenmiş bir .exe olarak çalışırken __file__ tabanlı yollar
    geçici/bundle dizinini gösterir - kalıcı veriler onun yerine
    build_exe.py'nin ürettiği paylaşılan üst klasörde (dist/
    KasaInspection/<UygulamaAdı>/<UygulamaAdı>.exe -> iki üst dizin)
    tutulmalı ki Launcher/Configurator/Inspection aynı band
    yapılandırmasını/ayarları görsün ve klasör elden ele taşınabilsin.
    """

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent.parent

    return Path(__file__).resolve().parents[2]


def get_resource_path(relative: str) -> Path:
    """
    Uygulama koduyla birlikte dağıtılan salt-okunur bir kaynağın
    (ör. assets/icon.png) yolu - kalıcı/kullanıcı verisinden
    (get_app_root) farklı olarak bu, PyInstaller ile paketlenmişken
    .exe'nin YANINDA değil, PyInstaller'ın bundle'ladığı _MEIPASS
    dizininde bulunur (bkz. build_exe.py --add-data).
    """

    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    else:
        base = Path(__file__).resolve().parents[2]

    return base / relative
