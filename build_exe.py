"""
Launcher/Configurator/Inspection'ı PyInstaller ile paketler.

Üç uygulama da AYRI onedir derlemesi olarak, ama TEK bir paylaşılan
üst klasörün (dist/KasaInspection/) altına, kardeş alt klasörler
halinde çıkar:

    dist/KasaInspection/
        Launcher/Launcher.exe
        Configurator/Configurator.exe
        Inspection/Inspection.exe

Bu düzen kasıtlı: Configurator ve Inspection aynı band
yapılandırmasını/ayarları görmeli, bu yüzden ikisinin de kalıcı veri
kök dizini (bkz. modules/utils/paths.get_app_root) exe'nin İKİ üst
dizinidir - yani hepsi dist/KasaInspection/ altında "configuration/",
"logs/", "window_settings.ini" paylaşır. Launcher.exe de kardeş
uygulamaları bu düzene göre bulur (bkz. apps/launcher.py _launch).

Çalıştırma:
    .venv\\Scripts\\python.exe build_exe.py
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST_DIR = ROOT / "dist" / "KasaInspection"
WORK_ROOT = ROOT / "build" / "pyinstaller"
ICON_PATH = ROOT / "assets" / "icon.ico"
ICON_PNG_PATH = ROOT / "assets" / "icon.png"

APPS = [
    ("Launcher", "apps/launcher.py"),
    ("Configurator", "apps/configurator.py"),
    ("Inspection", "apps/inspection.py"),
]


def build_app(name: str, entry: str):

    print(f"\n--- {name} paketleniyor ---")

    work_dir = WORK_ROOT / name

    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--name", name,
        "--distpath", str(DIST_DIR),
        "--workpath", str(work_dir),
        "--specpath", str(work_dir),
    ]

    if ICON_PATH.exists():
        args += ["--icon", str(ICON_PATH)]

    if ICON_PNG_PATH.exists():
        # Uygulama içi pencere/taskbar ikonu için (bkz.
        # modules/utils/paths.get_resource_path) - .exe dosya ikonu
        # ayrı olarak yukarıdaki --icon ile ayarlanır.
        args += ["--add-data", f"{ICON_PNG_PATH};assets"]

    args.append(str(ROOT / entry))

    subprocess.run(args, check=True, cwd=ROOT)


def main():

    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)

    for name, entry in APPS:
        build_app(name, entry)

    print(f"\nTamamlandı: {DIST_DIR}")
    print(
        "Band bilgisayarına taşırken KasaInspection klasörünün "
        "TAMAMINI (üç alt klasörle birlikte) kopyalayın."
    )


if __name__ == "__main__":
    main()
