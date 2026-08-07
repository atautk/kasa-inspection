import json

from PySide6.QtWidgets import (
    QInputDialog,
    QMessageBox,
    QListWidgetItem,
    QFileDialog
)
from PySide6.QtCore import Qt, QTimer

from modules.configuration.band import Band
from modules.configuration.band_manager import BandManager
from modules.configuration.reference_manager import ReferenceManager
from modules.configuration.model_manager import ModelManager
from modules.configuration.configuration_validator import ConfigurationValidator
from modules.configuration.band_export_manager import BandExportManager
from modules.utils.logger import get_logger

from modules.ui.configurator.operator_management_dialog import (
    OperatorManagementDialog
)
from modules.ui.configurator.audit_log_dialog import AuditLogDialog
from modules.ui.configurator.telegram_settings_dialog import (
    TelegramSettingsDialog
)
from modules.ui.configurator.telegram_recipients_dialog import (
    TelegramRecipientsDialog
)
from modules.ui.configurator.camera_channels_dialog import (
    CameraChannelsDialog
)
from modules.ui.configurator.arduino_settings_dialog import (
    ArduinoSettingsDialog
)
from modules.ui.configurator.shift_settings_dialog import (
    ShiftSettingsDialog
)
from modules.ui.configurator.reference_reminder_dialog import (
    ReferenceReminderDialog
)
from modules.ui.configurator.training_data_settings_dialog import (
    TrainingDataSettingsDialog
)
from modules.ui.configurator.auto_backup_settings_dialog import (
    AutoBackupSettingsDialog
)
from modules.configuration.telegram_settings_manager import (
    TelegramSettingsManager
)
from modules.configuration.telegram_recipients_manager import (
    TelegramRecipientsManager
)
from modules.utils.logger import LOG_FILE
from modules.utils.test_runner import TestRunner
from modules.utils.paths import get_app_root

ROOT = get_app_root()

from modules.core.camera import Camera
from modules.core.aruco_detector import ArucoDetector
from modules.core.localization import LocalizationEngine
from modules.core.reference_frame import ReferenceFrame
from modules.core.frame_processor import FrameProcessor
from modules.core.roi_auto_detector import ROIAutoDetector
from modules.core.blur_detector import BlurDetector

app_logger = get_logger()


class ConfiguratorController:

    def __init__(self, window, operator_name=None, operator_manager=None):

        self.window = window
        self.operator_name = operator_name or "?"
        self.operator_manager = operator_manager

        self.band_manager = BandManager(root=ROOT / "configuration")
        self.reference_manager = ReferenceManager()
        self.model_manager = ModelManager()
        self.validator = ConfigurationValidator()
        self.export_manager = BandExportManager()

        self.current_band = None
        self.current_model = None

        # ---------- Reference Capture ----------

        self.camera = None

        self.aruco = ArucoDetector()
        self.localizer = LocalizationEngine()
        self.reference_frame = ReferenceFrame()
        self.roi_auto_detector = ROIAutoDetector()
        self.blur_detector = BlurDetector()

        self.test_runner = TestRunner()
        self.test_runner.finished.connect(self._on_tests_finished)

        self.telegram_settings_manager = TelegramSettingsManager(
            ROOT / "configuration" / "telegram_settings.json"
        )
        self.telegram_recipients_manager = TelegramRecipientsManager(
            ROOT / "configuration" / "telegram_recipients.json"
        )

        self.frame_processor = FrameProcessor(
            self.aruco,
            self.localizer,
            self.reference_frame
        )

        self.last_reference_frame = None

        self.camera_timer = QTimer()
        self.camera_timer.setInterval(30)
        self.camera_timer.timeout.connect(
            self.update_camera_frame
        )

        self.connect_signals()

        self.load_bands()

        self.window.close_callback = self._on_window_closing

    # -------------------------------------------------
    # Pencere Kapanıyor
    # -------------------------------------------------

    def _on_window_closing(self):

        app_logger.info("[%s] çıkış yaptı (Configurator)", self.operator_name)

    # -------------------------------------------------
    # Sinyaller
    # -------------------------------------------------

    def connect_signals(self):

        band_page = self.window.band_page

        band_page.new_button.clicked.connect(
            self.create_band
        )

        band_page.open_button.clicked.connect(
            self.open_band
        )

        self.window.validate_action.triggered.connect(
            self.validate_band
        )

        self.window.export_action.triggered.connect(
            self.export_band
        )

        self.window.import_action.triggered.connect(
            self.import_band
        )

        self.window.manage_operators_action.triggered.connect(
            self.open_operator_management
        )

        self.window.audit_log_action.triggered.connect(
            self.open_audit_log
        )

        self.window.telegram_settings_action.triggered.connect(
            self.open_telegram_settings
        )

        self.window.telegram_recipients_action.triggered.connect(
            self.open_telegram_recipients
        )

        self.window.camera_channels_action.triggered.connect(
            self.open_camera_channels
        )

        self.window.arduino_settings_action.triggered.connect(
            self.open_arduino_settings
        )

        self.window.shift_settings_action.triggered.connect(
            self.open_shift_settings
        )

        self.window.reference_reminder_action.triggered.connect(
            self.open_reference_reminder
        )

        self.window.training_data_settings_action.triggered.connect(
            self.open_training_data_settings
        )

        self.window.auto_backup_settings_action.triggered.connect(
            self.open_auto_backup_settings
        )

        reference_page = self.window.reference_page

        reference_page.camera_button.clicked.connect(
            self.toggle_camera
        )

        reference_page.capture_button.clicked.connect(
            self.capture_reference
        )

        reference_page.retake_button.clicked.connect(
            self.retake_reference
        )

        reference_page.channel_combo.currentIndexChanged.connect(
            self.on_reference_channel_changed
        )

        roi_page = self.window.roi_page

        roi_page.save_button.clicked.connect(
            self.save_rois
        )

        roi_page.auto_detect_button.clicked.connect(
            self.auto_detect_rois
        )

        roi_page.channel_combo.currentIndexChanged.connect(
            self.on_roi_channel_changed
        )

        model_page = self.window.model_page

        model_page.new_button.clicked.connect(
            self.create_model
        )

        model_page.delete_button.clicked.connect(
            self.delete_model
        )

        model_page.save_button.clicked.connect(
            self.save_model
        )

        model_page.model_list.currentItemChanged.connect(
            self.on_model_selected
        )

        self.window.test_runner_page.run_button.clicked.connect(
            self.run_tests
        )

        self.window.tabs.currentChanged.connect(
            self.on_tab_changed
        )

    # -------------------------------------------------

    def on_tab_changed(self, index: int):

        if index == 2:

            self.load_roi_tab()

        elif index == 3:

            self.load_model_tab()

    # -------------------------------------------------
    # Test Çalıştırma
    # -------------------------------------------------

    def run_tests(self):

        if self.test_runner.is_running():
            return

        page = self.window.test_runner_page

        page.set_running(True)
        page.set_summary("Testler çalışıyor...")
        page.clear_results()

        self.test_runner.run()

    def _on_tests_finished(self, data: dict):

        page = self.window.test_runner_page

        page.set_running(False)
        page.set_summary(data["summary"])
        page.set_results(data["results"])

        app_logger.info(
            "[%s] testler çalıştırıldı: %s",
            self.operator_name,
            data["summary"]
        )

        if not data["success"]:

            for result in data["results"]:

                if result["status"] in ("failed", "error"):

                    app_logger.error(
                        "[%s] test hatası - %s:\n%s",
                        self.operator_name,
                        result["name"],
                        result["message"]
                    )

    # -------------------------------------------------
    # Band Yönetimi
    # -------------------------------------------------

    def load_bands(self):

        page = self.window.band_page

        page.band_list.clear()

        bands = self.band_manager.list_bands()

        for band in bands:

            item = QListWidgetItem(band.name)

            item.setData(Qt.UserRole, band.id)

            page.band_list.addItem(item)

    # -------------------------------------------------

    def create_band(self):

        name, ok = QInputDialog.getText(

            self.window,

            "Yeni Band",

            "Band Adı"

        )

        if not ok:
            return

        name = name.strip()

        if name == "":
            return

        self.band_manager.create_band(name)

        app_logger.info(
            "[%s] yeni band oluşturuldu: %s",
            self.operator_name,
            name
        )

        self.load_bands()

    # -------------------------------------------------

    def open_band(self):

        page = self.window.band_page

        item = page.band_list.currentItem()

        if item is None:

            QMessageBox.warning(

                self.window,

                "Uyarı",

                "Lütfen bir band seçin."

            )

            return

        band_id = item.data(Qt.UserRole)

        self.current_band = self.band_manager.load_band(band_id)

        self.window.setWindowTitle(

            f"KASA CONFIGURATOR - {self.current_band.name}"

        )

        # Reference sekmesi her zaman açılabilir.
        self.window.tabs.setTabEnabled(1, True)

        # ROI sekmesi, reference.png oluşmadan açılmaz.
        self._update_roi_tab_state()

        # Models sekmesi şimdilik serbest.
        self.window.tabs.setTabEnabled(3, True)

        self.window.camera_channels_action.setEnabled(True)
        self.window.arduino_settings_action.setEnabled(True)
        self.window.shift_settings_action.setEnabled(True)
        self.window.reference_reminder_action.setEnabled(True)
        self.window.training_data_settings_action.setEnabled(True)
        self.window.auto_backup_settings_action.setEnabled(True)

        self.load_reference_tab()

        QMessageBox.information(

            self.window,

            "Başarılı",

            f"{self.current_band.name} açıldı."

        )

    # -------------------------------------------------

    def open_arduino_settings(self):

        if self.current_band is None:
            return

        dialog = ArduinoSettingsDialog(
            self.current_band.arduino_port,
            self.window
        )

        if dialog.exec() != ArduinoSettingsDialog.Accepted:
            return

        self.current_band.arduino_port = dialog.get_port()

        self.band_manager.save_band(self.current_band)

        app_logger.info(
            "[%s] arduino portu değiştirildi: %s -> '%s'",
            self.operator_name,
            self.current_band.name,
            self.current_band.arduino_port
        )

    # -------------------------------------------------
    # Vardiya Ayarları
    # -------------------------------------------------

    def open_shift_settings(self):

        if self.current_band is None:
            return

        dialog = ShiftSettingsDialog(self.current_band, self.window)

        if dialog.exec() != ShiftSettingsDialog.Accepted:
            return

        self.current_band.shift_target_count = dialog.get_target_count()
        self.current_band.shift_duration_hours = dialog.get_duration_hours()

        self.band_manager.save_band(self.current_band)

        app_logger.info(
            "[%s] vardiya ayarları değiştirildi: %s -> hedef %d kasa / "
            "%.1f saat",
            self.operator_name,
            self.current_band.name,
            self.current_band.shift_target_count,
            self.current_band.shift_duration_hours
        )

    # -------------------------------------------------
    # Referans Yenileme Hatırlatıcısı
    # -------------------------------------------------

    def open_reference_reminder(self):

        if self.current_band is None:
            return

        dialog = ReferenceReminderDialog(self.current_band, self.window)

        if dialog.exec() != ReferenceReminderDialog.Accepted:
            return

        self.current_band.reference_max_age_days = (
            dialog.get_max_age_days()
        )

        self.band_manager.save_band(self.current_band)

        app_logger.info(
            "[%s] referans yenileme hatırlatıcısı değiştirildi: %s -> "
            "%d gün",
            self.operator_name,
            self.current_band.name,
            self.current_band.reference_max_age_days
        )

    # -------------------------------------------------
    # Model Eğitimi Veri Toplama
    # -------------------------------------------------

    def open_training_data_settings(self):

        if self.current_band is None:
            return

        dialog = TrainingDataSettingsDialog(self.current_band, self.window)

        if dialog.exec() != TrainingDataSettingsDialog.Accepted:
            return

        self.current_band.training_data_collection_enabled = (
            dialog.is_enabled()
        )

        self.band_manager.save_band(self.current_band)

        app_logger.info(
            "[%s] model eğitimi veri toplama değiştirildi: %s -> %s",
            self.operator_name,
            self.current_band.name,
            self.current_band.training_data_collection_enabled
        )

    # -------------------------------------------------
    # Otomatik Yedekleme
    # -------------------------------------------------

    def open_auto_backup_settings(self):

        if self.current_band is None:
            return

        dialog = AutoBackupSettingsDialog(self.current_band, self.window)

        if dialog.exec() != AutoBackupSettingsDialog.Accepted:
            return

        self.current_band.auto_backup_enabled = dialog.is_enabled()
        self.current_band.auto_backup_destination = dialog.get_destination()
        self.current_band.auto_backup_interval_hours = (
            dialog.get_interval_hours()
        )
        self.current_band.auto_backup_keep_count = dialog.get_keep_count()

        self.band_manager.save_band(self.current_band)

        app_logger.info(
            "[%s] otomatik yedekleme ayarları değiştirildi: %s -> "
            "açık=%s, hedef=%s, sıklık=%.1f saat, sakla=%d",
            self.operator_name,
            self.current_band.name,
            self.current_band.auto_backup_enabled,
            self.current_band.auto_backup_destination,
            self.current_band.auto_backup_interval_hours,
            self.current_band.auto_backup_keep_count
        )

    # -------------------------------------------------
    # Kamera Kanalları (Çoklu Açı)
    # -------------------------------------------------

    def open_camera_channels(self):

        if self.current_band is None:
            return

        before = {channel.id for channel in self.current_band.cameras}

        dialog = CameraChannelsDialog(
            self.band_manager,
            self.current_band,
            self.window
        )

        dialog.exec()

        after = {channel.id for channel in self.current_band.cameras}

        if before != after:

            app_logger.info(
                "[%s] kamera kanalları güncellendi: %s (%d kanal)",
                self.operator_name,
                self.current_band.name,
                len(self.current_band.cameras)
            )

        # Reference/ROI sekmelerindeki kanal seçim kutuları, band
        # kapanmadan önceki kanal listesini gösteriyor olabilir -
        # pencere kapandığında her durumda tazeleriz.
        self._refresh_camera_selectors()

    # -------------------------------------------------

    def validate_band(self):

        page = self.window.band_page

        item = page.band_list.currentItem()

        if item is None:

            QMessageBox.warning(

                self.window,

                "Uyarı",

                "Lütfen doğrulanacak bir band seçin."

            )

            return

        band_id = item.data(Qt.UserRole)

        band = self.band_manager.load_band(band_id)

        result = self.validator.validate(band)

        if result["valid"]:

            QMessageBox.information(

                self.window,

                "Doğrulama Başarılı",

                f"{band.name} yapılandırması eksiksiz."

            )

        else:

            message = "\n".join(
                f"- {error}"
                for error in result["errors"]
            )

            QMessageBox.warning(

                self.window,

                "Doğrulama Başarısız",

                f"{band.name} yapılandırmasında sorunlar var:\n\n"
                f"{message}"

            )

    # -------------------------------------------------
    # Dışa / İçe Aktar
    # -------------------------------------------------

    def export_band(self):

        page = self.window.band_page

        item = page.band_list.currentItem()

        if item is None:

            QMessageBox.warning(
                self.window,
                "Uyarı",
                "Lütfen dışa aktarılacak bir band seçin."
            )

            return

        band_id = item.data(Qt.UserRole)

        band = self.band_manager.load_band(band_id)

        path, _ = QFileDialog.getSaveFileName(
            self.window,
            "Bandı Dışa Aktar",
            f"{band.name}.zip",
            "Zip Dosyası (*.zip)"
        )

        if not path:
            return

        try:

            self.export_manager.export_band(band, path)

        except Exception as e:

            QMessageBox.critical(
                self.window,
                "Hata",
                f"Dışa aktarma başarısız: {e}"
            )

            return

        QMessageBox.information(
            self.window,
            "Başarılı",
            f"{band.name} şu dosyaya aktarıldı:\n{path}"
        )

    # -------------------------------------------------

    def import_band(self):

        path, _ = QFileDialog.getOpenFileName(
            self.window,
            "Band İçe Aktar",
            "",
            "Zip Dosyası (*.zip)"
        )

        if not path:
            return

        try:

            band = self.export_manager.import_band(
                self.band_manager,
                path
            )

        except Exception as e:

            QMessageBox.critical(
                self.window,
                "Hata",
                f"İçe aktarma başarısız: {e}"
            )

            return

        self.load_bands()

        QMessageBox.information(
            self.window,
            "Başarılı",
            f"{band.name} yeni bir band olarak içe aktarıldı."
        )

    # -------------------------------------------------
    # Operatör Yönetimi
    # -------------------------------------------------

    def open_operator_management(self):

        if self.operator_manager is None:
            return

        if not self.operator_manager.is_admin(self.operator_name):

            QMessageBox.warning(
                self.window,
                "Yetkisiz",
                "Bu işlem için yönetici yetkisi gereklidir."
            )

            return

        dialog = OperatorManagementDialog(
            self.operator_manager,
            self.window
        )

        dialog.exec()

    # -------------------------------------------------

    def open_audit_log(self):

        if self.operator_manager is None:
            return

        if not self.operator_manager.is_admin(self.operator_name):

            QMessageBox.warning(
                self.window,
                "Yetkisiz",
                "Bu işlem için yönetici yetkisi gereklidir."
            )

            return

        dialog = AuditLogDialog(LOG_FILE, self.window)

        dialog.exec()

    # -------------------------------------------------

    def open_telegram_settings(self):

        if self.operator_manager is None:
            return

        if not self.operator_manager.is_admin(self.operator_name):

            QMessageBox.warning(
                self.window,
                "Yetkisiz",
                "Bu işlem için yönetici yetkisi gereklidir."
            )

            return

        dialog = TelegramSettingsDialog(
            self.telegram_settings_manager,
            self.window
        )

        dialog.exec()

    # -------------------------------------------------

    def open_telegram_recipients(self):

        if self.operator_manager is None:
            return

        if not self.operator_manager.is_admin(self.operator_name):

            QMessageBox.warning(
                self.window,
                "Yetkisiz",
                "Bu işlem için yönetici yetkisi gereklidir."
            )

            return

        dialog = TelegramRecipientsDialog(
            self.telegram_settings_manager,
            self.telegram_recipients_manager,
            self.window
        )

        dialog.exec()

    # -------------------------------------------------
    # Kamera Kanalı Yardımcıları (Reference/ROI sekmeleri ortak)
    # -------------------------------------------------

    def _camera_targets(self) -> list:
        """
        (etiket, channel_id_ya_da_None, target) üçlülerini döndürür.
        target: birincil kamera için Band'in kendisi, ek kanallar
        için ilgili CameraChannel nesnesi.
        """

        targets = [("Birincil Kamera", None, self.current_band)]

        for channel in self.current_band.cameras:
            targets.append((channel.name, channel.id, channel))

        return targets

    def _camera_target_by_id(self, channel_id):

        for label, target_id, target in self._camera_targets():

            if target_id == channel_id:
                return target

        return self.current_band

    def _camera_index_of(self, target) -> int:

        if isinstance(target, Band):
            return target.camera

        return target.camera_index

    def _refresh_camera_selectors(self):
        """
        Bir kanal eklendiğinde/silindiğinde, Reference ve ROI
        sekmelerindeki kanal seçim kutularını güncel listeyle
        yeniden doldurur (seçili kanalı korumaya çalışarak).
        """

        if self.current_band is None:
            return

        items = [
            (label, channel_id)
            for label, channel_id, _ in self._camera_targets()
        ]

        for page in (
            self.window.reference_page,
            self.window.roi_page
        ):

            current = page.get_selected_channel_id()

            page.set_channels(items)

            index = page.channel_combo.findData(current)

            page.channel_combo.setCurrentIndex(index if index >= 0 else 0)

    # -------------------------------------------------
    # Reference Sekmesi
    # -------------------------------------------------

    def load_reference_tab(self):

        self.stop_camera()

        page = self.window.reference_page

        page.set_channels([
            (label, channel_id)
            for label, channel_id, _ in self._camera_targets()
        ])

        self._show_reference_for_selected_channel()

    # -------------------------------------------------

    def on_reference_channel_changed(self):

        self.stop_camera()
        self._show_reference_for_selected_channel()

    # -------------------------------------------------

    def _show_reference_for_selected_channel(self):

        page = self.window.reference_page

        target = self._current_reference_target()

        self.last_reference_frame = None

        if self.reference_manager.exists(target):

            image = self.reference_manager.load(target)

            page.set_preview(image)
            page.set_status("Kayıtlı reference bulundu")
            page.set_marker_status("-")

            page.enable_camera_button(True)
            page.enable_capture(False)
            page.enable_retake_button(True)

        else:

            page.clear_preview()
            page.set_status("Reference yok. Kamerayı açın.")
            page.set_marker_status("-")
            page.set_resolution(0, 0)

            page.enable_camera_button(True)
            page.enable_capture(False)
            page.enable_retake_button(False)

    # -------------------------------------------------

    def _current_reference_target(self):

        channel_id = self.window.reference_page.get_selected_channel_id()

        return self._camera_target_by_id(channel_id)

    # -------------------------------------------------

    def toggle_camera(self):

        if self.camera is not None and self.camera.is_open():

            self.stop_camera()

        else:

            self.start_camera()

    # -------------------------------------------------

    def start_camera(self):

        if self.current_band is None:
            return

        page = self.window.reference_page

        target = self._current_reference_target()

        self.camera = Camera(
            camera_index=self._camera_index_of(target)
        )

        if not self.camera.open():

            QMessageBox.critical(

                self.window,

                "Hata",

                "Kamera açılamadı."

            )

            self.camera = None
            return

        # Her kamera açılışında localizer/reference_frame
        # sıfırdan başlasın (eski recovery state kalmasın).

        self.localizer = LocalizationEngine()
        self.reference_frame = ReferenceFrame()

        self.frame_processor = FrameProcessor(
            self.aruco,
            self.localizer,
            self.reference_frame
        )

        self.last_reference_frame = None

        page.camera_button.setText("Kamerayı Kapat")
        page.set_status("Kamera açık, hizalama bekleniyor...")
        page.enable_capture(False)

        self.camera_timer.start()

    # -------------------------------------------------

    def stop_camera(self):

        self.camera_timer.stop()

        if self.camera is not None:

            self.camera.release()
            self.camera = None

        page = self.window.reference_page
        page.camera_button.setText("Kamera Aç")

    # -------------------------------------------------

    def update_camera_frame(self):

        if self.camera is None:
            return

        frame = self.camera.read()

        if frame is None:
            return

        page = self.window.reference_page

        result = self.frame_processor.process(frame)

        if not result["success"]:

            page.set_status(f"Hata: {result['error']}")
            return

        localization = result["localization"]
        reference = result["reference"]

        page.set_marker_status(
            f"{localization['visible']} / 4 "
            f"({localization['mode']})"
        )

        if reference is not None:

            self.last_reference_frame = reference

            page.set_preview(reference)

            page.set_status(
                f"Hizalandı - Güven: {localization['confidence']}%"
            )

            page.enable_capture(True)

        else:

            self.last_reference_frame = None

            page.set_preview(frame)
            page.set_status("ArUco bulunamadı")
            page.enable_capture(False)

    # -------------------------------------------------

    def capture_reference(self):

        if self.last_reference_frame is None:
            return

        if self.current_band is not None:

            sharpness = self.blur_detector.compute_sharpness(
                self.last_reference_frame
            )

            if sharpness < self.current_band.blur_threshold:

                answer = QMessageBox.question(
                    self.window,
                    "Bulanık Görünüyor",
                    f"Bu fotoğraf bulanık görünüyor (netlik: "
                    f"{sharpness:.1f}, eşik: "
                    f"{self.current_band.blur_threshold:.1f}). Lens "
                    "kirli/buğulu olabilir ya da odak kaymış olabilir. "
                    "Yine de kaydetmek istiyor musunuz?"
                )

                if answer != QMessageBox.Yes:
                    return

        target = self._current_reference_target()

        self.reference_manager.save(

            target,

            self.last_reference_frame

        )

        self.stop_camera()

        page = self.window.reference_page

        page.set_preview(self.last_reference_frame)
        page.set_status("reference.png kaydedildi")
        page.enable_capture(False)
        page.enable_retake_button(True)

        self._update_roi_tab_state()

        QMessageBox.information(

            self.window,

            "Başarılı",

            "Reference kaydedildi. ROI sekmesi kullanılabilir."

        )

    # -------------------------------------------------

    def retake_reference(self):

        answer = QMessageBox.question(

            self.window,

            "Emin misiniz?",

            "Mevcut reference silinip yeniden çekilecek. "
            "Devam edilsin mi?"

        )

        if answer != QMessageBox.Yes:
            return

        self.reference_manager.delete(self._current_reference_target())

        self.last_reference_frame = None

        page = self.window.reference_page

        page.clear_preview()
        page.set_status("Reference silindi. Kamerayı açın.")
        page.enable_retake_button(False)
        page.enable_capture(False)

        self._update_roi_tab_state()

        self.start_camera()

    # -------------------------------------------------
    # ROI Sekmesi
    # -------------------------------------------------

    def load_roi_tab(self):

        if self.current_band is None:
            return

        page = self.window.roi_page

        page.set_channels([
            (label, channel_id)
            for label, channel_id, _ in self._camera_targets()
        ])

        self._show_roi_for_selected_channel()

    # -------------------------------------------------

    def on_roi_channel_changed(self):

        self._show_roi_for_selected_channel()

    # -------------------------------------------------

    def _show_roi_for_selected_channel(self):

        page = self.window.roi_page

        target = self._current_roi_target()

        if not self.reference_manager.exists(target):

            page.clear()
            page.set_status(
                "Bu kanal için reference bulunamadı. Önce Reference "
                "sekmesinden fotoğraf çekin."
            )
            return

        image = self.reference_manager.load(target)
        page.set_background(image)

        rois = self._read_roi_file(target.roi)
        page.load_rois(rois)

        page.set_status(
            f"{len(rois)} ROI yüklendi."
        )

    # -------------------------------------------------

    def _current_roi_target(self):

        channel_id = self.window.roi_page.get_selected_channel_id()

        return self._camera_target_by_id(channel_id)

    # -------------------------------------------------

    def save_rois(self):

        if self.current_band is None:
            return

        target = self._current_roi_target()

        rois = self.window.roi_page.get_rois()

        data = {
            "version": "1.0",
            "rois": rois
        }

        with open(
            target.roi,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )

        self.window.roi_page.set_status(
            f"{len(rois)} ROI kaydedildi."
        )

        channel_label = (
            "Birincil" if isinstance(target, Band) else target.name
        )

        app_logger.info(
            "[%s] ROI'ler kaydedildi: %s / %s (%d ROI)",
            self.operator_name,
            self.current_band.name,
            channel_label,
            len(rois)
        )

        QMessageBox.information(

            self.window,

            "Başarılı",

            f"{len(rois)} ROI roi.json dosyasına kaydedildi."

        )

    # -------------------------------------------------

    def auto_detect_rois(self):

        if self.current_band is None:
            return

        target = self._current_roi_target()

        if not self.reference_manager.exists(target):

            QMessageBox.warning(
                self.window,
                "Uyarı",
                "Önce Reference sekmesinden fotoğraf çekin."
            )

            return

        image = self.reference_manager.load(target)

        detected = self.roi_auto_detector.detect(image)

        if not detected:

            QMessageBox.information(
                self.window,
                "Sonuç Yok",
                "Otomatik ROI bulunamadı. Kasa gözleri arasında "
                "belirgin bir çizgi/duvar olması gerekiyor."
            )

            return

        page = self.window.roi_page

        existing_count = len(page.get_rois())

        if existing_count > 0:

            answer = QMessageBox.question(
                self.window,
                "Emin misiniz?",
                f"Mevcut {existing_count} ROI silinip otomatik "
                f"bulunan {len(detected)} ROI ile değiştirilecek. "
                "Devam edilsin mi?"
            )

            if answer != QMessageBox.Yes:
                return

        rois = [
            {"id": "", "name": f"G{i + 1:02d}", "points": points}
            for i, points in enumerate(detected)
        ]

        page.load_rois(rois)

        page.set_status(
            f"{len(rois)} ROI otomatik bulundu. Kontrol edip "
            "Kaydet'e basın."
        )

        app_logger.info(
            "[%s] otomatik ROI bulundu: %s (%d ROI)",
            self.operator_name,
            self.current_band.name,
            len(rois)
        )

    # -------------------------------------------------

    def _read_roi_file(self, roi_file=None) -> list:

        if roi_file is None:
            roi_file = self.current_band.roi

        if not roi_file.exists():
            return []

        try:

            with open(
                roi_file,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

            return data.get("rois", [])

        except Exception:

            return []

    # -------------------------------------------------
    # Model Sekmesi
    # -------------------------------------------------

    def load_model_tab(self):

        if self.current_band is None:
            return

        page = self.window.model_page

        models = self.model_manager.list_models(
            self.current_band
        )

        page.set_models([
            {"id": model.id, "name": model.name}
            for model in models
        ])

        page.clear_roi_checklist()

        if self.reference_manager.exists(self.current_band):
            page.set_reference_image(
                self.reference_manager.load(self.current_band)
            )
        else:
            page.set_reference_image(None)

        page.set_roi_shapes(self._read_roi_file())

        self.current_model = None
        page.set_marker_id(None)

        page.set_status(f"{len(models)} model bulundu.")

    # -------------------------------------------------

    def on_model_selected(self, current, previous):

        page = self.window.model_page

        model_id = page.get_selected_model_id()

        if model_id is None:

            self.current_model = None
            page.clear_roi_checklist()
            page.set_marker_id(None)
            return

        self.current_model = self.model_manager.load_model(
            self.current_band,
            model_id
        )

        roi_names = self._roi_names()

        page.set_roi_checklist(
            roi_names,
            self.current_model.expected_rois,
            self.current_model.roi_thresholds
        )

        page.set_marker_id(self.current_model.marker_id)

        page.set_status(f"{self.current_model.name} yüklendi.")

    # -------------------------------------------------

    def create_model(self):

        if self.current_band is None:
            return

        name, ok = QInputDialog.getText(

            self.window,

            "Yeni Model",

            "Model Adı"

        )

        if not ok:
            return

        name = name.strip()

        if name == "":
            return

        self.model_manager.create_model(
            self.current_band,
            name
        )

        app_logger.info(
            "[%s] yeni model oluşturuldu: %s / %s",
            self.operator_name,
            self.current_band.name,
            name
        )

        self.load_model_tab()

    # -------------------------------------------------

    def delete_model(self):

        page = self.window.model_page

        model_id = page.get_selected_model_id()

        if model_id is None:

            QMessageBox.warning(

                self.window,

                "Uyarı",

                "Lütfen bir model seçin."

            )

            return

        answer = QMessageBox.question(

            self.window,

            "Emin misiniz?",

            "Model silinecek. Devam edilsin mi?"

        )

        if answer != QMessageBox.Yes:
            return

        self.model_manager.delete_model(
            self.current_band,
            model_id
        )

        app_logger.info(
            "[%s] model silindi: %s / %s",
            self.operator_name,
            self.current_band.name,
            model_id
        )

        self.load_model_tab()

    # -------------------------------------------------

    def save_model(self):

        if self.current_model is None:

            QMessageBox.warning(

                self.window,

                "Uyarı",

                "Lütfen bir model seçin."

            )

            return

        page = self.window.model_page

        self.current_model.expected_rois = (
            page.get_checked_rois()
        )

        self.current_model.roi_thresholds = (
            page.get_roi_thresholds()
        )

        marker_id = page.get_marker_id()

        if marker_id in (1, 2, 3):

            QMessageBox.warning(

                self.window,

                "Uyarı",

                "1, 2, 3 sabit köşe marker'ları için ayrılmıştır, "
                "tanı ID'si olarak kullanılamaz."

            )

            return

        if marker_id is not None:

            for other in self.model_manager.list_models(self.current_band):

                if (
                    other.id != self.current_model.id
                    and other.marker_id == marker_id
                ):

                    QMessageBox.warning(

                        self.window,

                        "Uyarı",

                        f"Marker ID {marker_id} zaten '{other.name}' "
                        "modelinde kullanılıyor."

                    )

                    return

        self.current_model.marker_id = marker_id

        self.model_manager.save_model(
            self.current_band,
            self.current_model
        )

        app_logger.info(
            "[%s] model kaydedildi: %s / %s -> beklenen ROI'ler: %s, "
            "eşik override'ları: %s, marker ID: %s",
            self.operator_name,
            self.current_band.name,
            self.current_model.name,
            self.current_model.expected_rois,
            self.current_model.roi_thresholds,
            self.current_model.marker_id
        )

        page.set_status(
            f"{self.current_model.name} kaydedildi."
        )

        QMessageBox.information(

            self.window,

            "Başarılı",

            f"{self.current_model.name} kaydedildi."

        )

    # -------------------------------------------------

    def _roi_names(self) -> list:
        """
        Model editöründeki "Beklenen Durum" tablosunda kullanılacak
        tüm ROI isimlerini döndürür: birincil kameranın isimleri
        olduğu gibi, ek kamera kanallarının isimleri ise
        PrefixedRecipeAdapter ile aynı kurala göre "KanalAdı:ROI"
        şeklinde nitelenmiş olarak.
        """

        names = [
            roi.get("name", "")
            for roi in self._read_roi_file()
        ]

        for channel in self.current_band.cameras:

            channel_roi_names = [
                roi.get("name", "")
                for roi in self._read_roi_file(channel.roi)
            ]

            names.extend(
                f"{channel.name}:{name}"
                for name in channel_roi_names
            )

        return names

    # -------------------------------------------------
    # Yardımcılar
    # -------------------------------------------------

    def _update_roi_tab_state(self):

        has_reference = self.reference_manager.exists(
            self.current_band
        )

        self.window.tabs.setTabEnabled(2, has_reference)