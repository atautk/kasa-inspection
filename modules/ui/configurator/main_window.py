import sys

from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget
)

from .band_page import BandPage
from .reference_page import ReferencePage
from .roi_page import ROIPage
from .model_page import ModelPage
from .test_runner_page import TestRunnerPage
from ..common.accessibility_dialog import AccessibilityDialog

from ..window_utils import restore_or_center, save_geometry

SETTINGS_KEY = "configurator_main"


class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("KASA CONFIGURATOR")

        restore_or_center(self, SETTINGS_KEY, 1400, 900)

        self.tabs = QTabWidget()

        self.band_page = BandPage()
        self.reference_page = ReferencePage()
        self.roi_page = ROIPage()
        self.model_page = ModelPage()
        self.test_runner_page = TestRunnerPage()

        self.tabs.addTab(self.band_page, "Band")
        self.tabs.addTab(self.reference_page, "Reference")
        self.tabs.addTab(self.roi_page, "ROI")
        self.tabs.addTab(self.model_page, "Models")

        # Paketlenmiş .exe'de pytest/tests/ klasörü bulunmadığından bu
        # sekme çalışmaz - sadece geliştirme ortamında (python ile
        # çalıştırılınca) gösterilir. test_runner_page yine de
        # oluşturulur (ConfiguratorController sinyal bağlarken ona
        # erişiyor), sadece sekme listesine eklenmez.
        if not getattr(sys, "frozen", False):
            self.tabs.addTab(self.test_runner_page, "Testler")

        self.tabs.setTabEnabled(1, False)
        self.tabs.setTabEnabled(2, False)
        self.tabs.setTabEnabled(3, False)

        self.setCentralWidget(self.tabs)

        self.close_callback = None

        self._build_menu()

    # -------------------------------------------------

    def _build_menu(self):

        view_menu = self.menuBar().addMenu("&Görünüm")

        accessibility_action = view_menu.addAction(
            "&Erişebilirlik Ayarları..."
        )
        accessibility_action.triggered.connect(
            self._open_accessibility_dialog
        )

        self._build_management_menu()

    # -------------------------------------------------

    def _build_management_menu(self):
        """
        Seyrek kullanılan band-yönetimi işleri (doğrulama, dışa/içe
        aktarma, operatör/log, Telegram, kamera kanalı/Arduino
        ayarları) burada birer QAction olarak durur. Davranışları
        ConfiguratorController.connect_signals() tarafından bağlanır -
        bu sınıf sadece menüyü kurar, hiçbir iş mantığı bilmez.
        """

        management_menu = self.menuBar().addMenu("&Yönetim")

        self.validate_action = management_menu.addAction("Doğrula")
        self.export_action = management_menu.addAction("Dışa Aktar...")
        self.import_action = management_menu.addAction("İçe Aktar...")

        management_menu.addSeparator()

        self.manage_operators_action = management_menu.addAction(
            "Operatörleri Yönet..."
        )
        self.audit_log_action = management_menu.addAction(
            "Giriş/Çıkış ve Değişiklik Logu..."
        )

        management_menu.addSeparator()

        self.telegram_settings_action = management_menu.addAction(
            "Telegram Bildirimleri..."
        )
        self.telegram_recipients_action = management_menu.addAction(
            "Bildirim Alıcıları (Telefon Numarası)..."
        )

        management_menu.addSeparator()

        self.camera_channels_action = management_menu.addAction(
            "Kamera Kanallarını Yönet..."
        )
        self.camera_channels_action.setEnabled(False)

        self.arduino_settings_action = management_menu.addAction(
            "Arduino Ayarları..."
        )
        self.arduino_settings_action.setEnabled(False)

        self.shift_settings_action = management_menu.addAction(
            "Vardiya Ayarları..."
        )
        self.shift_settings_action.setEnabled(False)

        self.reference_reminder_action = management_menu.addAction(
            "Referans Yenileme Hatırlatıcısı..."
        )
        self.reference_reminder_action.setEnabled(False)

        self.training_data_settings_action = management_menu.addAction(
            "Model Eğitimi Veri Toplama..."
        )
        self.training_data_settings_action.setEnabled(False)

        self.auto_backup_settings_action = management_menu.addAction(
            "Otomatik Yedekleme..."
        )
        self.auto_backup_settings_action.setEnabled(False)

    def _open_accessibility_dialog(self):

        dialog = AccessibilityDialog(self)
        dialog.exec()

    # -------------------------------------------------

    def closeEvent(self, event):

        if self.close_callback is not None:
            self.close_callback()

        save_geometry(self, SETTINGS_KEY)

        super().closeEvent(event)