"""
Uygulama genelinde uygulanan açık/sade görsel tema (QSS).

Sadece yapısal "kabuk" (buton, sekme, tablo başlığı, kenarlık, giriş
kutuları) stillendirilir. UYGUN/HATA renkleri (bkz.
accessibility_settings.get_ok_color_*/get_ng_color_*) ve tek tek
widget'lara `setStyleSheet(...)` ile uygulanan banner/etiket renkleri
buradan ETKİLENMEZ - Qt'de widget'a doğrudan uygulanan stil her zaman
üst düzey (uygulama) stilinden önceliklidir. Tablo satır/hücre
renkleri de (UYGUN=yeşilimsi, HATA=kırmızımsı arka plan) kod
içinde `setBackground(...)` ile ayarlandığından, buradaki QSS bilerek
`QTableWidget::item` arka planına dokunmaz - dokunursa bu özel
renkleri bastırabilir.
"""

from modules.utils.paths import get_resource_path

# QSS url() ters slash'ı yol ayracı olarak tanımıyor, işletim
# sisteminden bağımsız hep ileri slash kullanılmalı.
CHEVRON_DOWN_URL = get_resource_path("assets/chevron_down.png").as_posix()
CHEVRON_DOWN_ACCENT_URL = get_resource_path(
    "assets/chevron_down_accent.png"
).as_posix()

BACKGROUND = "#F7F8FA"
SURFACE = "#FFFFFF"
BORDER = "#D9DCE3"
BORDER_STRONG = "#C3C8D2"
TEXT = "#1F2430"
TEXT_MUTED = "#6B7280"
ACCENT = "#2F6FED"
ACCENT_HOVER = "#2559C4"
ACCENT_PRESSED = "#1E4AA8"
DISABLED_BG = "#EEF0F3"
DISABLED_TEXT = "#9AA1AC"
SELECTION_BG = "#DCE7FC"

STYLESHEET = f"""
QWidget {{
    background-color: {BACKGROUND};
    color: {TEXT};
}}

QMainWindow, QDialog {{
    background-color: {BACKGROUND};
}}

QToolTip {{
    background-color: {TEXT};
    color: {SURFACE};
    border: none;
    padding: 4px 8px;
    border-radius: 4px;
}}

/* ---------- Butonlar ---------- */

QPushButton {{
    background-color: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER_STRONG};
    border-radius: 5px;
    padding: 6px 16px;
}}

QPushButton:hover {{
    border-color: {ACCENT};
    color: {ACCENT};
}}

QPushButton:pressed {{
    background-color: {SELECTION_BG};
}}

QPushButton:disabled {{
    background-color: {DISABLED_BG};
    color: {DISABLED_TEXT};
    border-color: {BORDER};
}}

QPushButton:checked {{
    background-color: {ACCENT};
    color: {SURFACE};
    border-color: {ACCENT_HOVER};
}}

QPushButton:default {{
    background-color: {ACCENT};
    color: {SURFACE};
    border-color: {ACCENT_HOVER};
}}

QPushButton:default:hover {{
    background-color: {ACCENT_HOVER};
    color: {SURFACE};
}}

QPushButton:default:pressed {{
    background-color: {ACCENT_PRESSED};
}}

/* ---------- Sekmeler ---------- */

QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 4px;
    background-color: {SURFACE};
    top: -1px;
}}

QTabBar::tab {{
    background-color: transparent;
    color: {TEXT_MUTED};
    padding: 8px 18px;
    border: none;
    border-bottom: 2px solid transparent;
}}

QTabBar::tab:hover {{
    color: {TEXT};
}}

QTabBar::tab:selected {{
    color: {ACCENT};
    border-bottom: 2px solid {ACCENT};
    font-weight: 600;
}}

QTabBar::tab:disabled {{
    color: {DISABLED_TEXT};
}}

/* ---------- Grup Kutuları ---------- */

QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 5px;
    margin-top: 14px;
    padding-top: 10px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: {TEXT_MUTED};
}}

/* ---------- Giriş Kutuları ---------- */

QLineEdit, QSpinBox, QDoubleSpinBox, QTimeEdit, QComboBox {{
    background-color: {SURFACE};
    border: 1px solid {BORDER_STRONG};
    border-radius: 4px;
    padding: 4px 6px;
    selection-background-color: {SELECTION_BG};
    selection-color: {TEXT};
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QTimeEdit:focus, QComboBox:focus {{
    border-color: {ACCENT};
}}

QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled,
QTimeEdit:disabled, QComboBox:disabled {{
    background-color: {DISABLED_BG};
    color: {DISABLED_TEXT};
}}

/* Bir kez QComboBox'ın kendisi stillendirilince Qt'nin platform
   aşağı-ok ikonunu otomatik çizmesi durur - kenarlık hilesiyle
   (border trick) çizilen ok bu Qt/stil kombinasyonunda görünmedi,
   bu yüzden küçük bir PNG ikonla (assets/chevron_down*.png) elle
   sağlanıyor. İkon olmadan kutunun çekmeceli (tıklanabilir liste)
   olduğu hiç belli olmuyordu. */

QComboBox {{
    padding-right: 24px;
}}

QComboBox::drop-down {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 22px;
    border: none;
}}

QComboBox::down-arrow {{
    image: url("{CHEVRON_DOWN_URL}");
    width: 10px;
    height: 10px;
    subcontrol-origin: border;
    subcontrol-position: center right;
    right: 6px;
}}

QComboBox::down-arrow:on {{
    image: url("{CHEVRON_DOWN_ACCENT_URL}");
}}

QComboBox QAbstractItemView {{
    background-color: {SURFACE};
    border: 1px solid {BORDER_STRONG};
    selection-background-color: {SELECTION_BG};
    selection-color: {TEXT};
}}

/* ---------- Onay Kutuları ---------- */

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {BORDER_STRONG};
    border-radius: 3px;
    background-color: {SURFACE};
}}

QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT_HOVER};
}}

QCheckBox::indicator:disabled {{
    background-color: {DISABLED_BG};
}}

/* ---------- Tablolar / Listeler ---------- */

QTableWidget, QListWidget {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 4px;
    gridline-color: {BORDER};
}}

QTableWidget::item:selected, QListWidget::item:selected {{
    background-color: {SELECTION_BG};
    color: {TEXT};
}}

QHeaderView::section {{
    background-color: {BACKGROUND};
    color: {TEXT_MUTED};
    border: none;
    border-bottom: 1px solid {BORDER_STRONG};
    border-right: 1px solid {BORDER};
    padding: 5px 6px;
    font-weight: 600;
}}

/* ---------- Menü ---------- */

QMenuBar {{
    background-color: {SURFACE};
    border-bottom: 1px solid {BORDER};
}}

QMenuBar::item:selected {{
    background-color: {SELECTION_BG};
}}

QMenu {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
}}

QMenu::item:selected {{
    background-color: {SELECTION_BG};
}}

/* ---------- Kaydırma Çubukları ---------- */

QScrollBar:vertical {{
    background: transparent;
    width: 12px;
}}

QScrollBar::handle:vertical {{
    background: {BORDER_STRONG};
    border-radius: 5px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: {TEXT_MUTED};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 12px;
}}

QScrollBar::handle:horizontal {{
    background: {BORDER_STRONG};
    border-radius: 5px;
    min-width: 24px;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
"""


def apply_light_theme(app):
    """
    Windows'un yerel stili ("windowsvista"), QComboBox gibi karmaşık
    widget'ların alt kontrollerini (::drop-down, ::down-arrow gibi)
    QSS ile özelleştirmeyi büyük ölçüde yok sayar - bu yüzden aşağı
    ok ikonu hiç görünmüyordu. "Fusion" stili QSS alt kontrol
    özelleştirmesini tam destekler, bu yüzden tema uygulanmadan önce
    ona geçiliyor.
    """

    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
