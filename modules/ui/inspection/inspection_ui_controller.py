import time
import winsound
from pathlib import Path

import cv2

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox

from modules.core.aruco_detector import ArucoDetector
from modules.core.localization import LocalizationEngine
from modules.core.reference_frame import ReferenceFrame
from modules.core.inspection_engine import InspectionEngine
from modules.core.decision_engine import DecisionEngine
from modules.core.blur_detector import BlurDetector

from modules.configuration.band_manager import BandManager
from modules.configuration.model_manager import ModelManager
from modules.configuration.reference_manager import ReferenceManager
from modules.configuration.model_recipe_adapter import (
    ModelRecipeAdapter,
    PrefixedRecipeAdapter
)
from modules.configuration.inspection_logger import InspectionLogger
from modules.configuration.ng_capture_manager import NGCaptureManager
from modules.configuration.training_data_manager import TrainingDataManager
from modules.configuration.backup_manager import BackupManager
from modules.configuration.data_retention_manager import DataRetentionManager
from modules.configuration.unknown_kasa_capture_manager import (
    UnknownKasaCaptureManager
)
from modules.configuration.configuration_validator import ConfigurationValidator
from modules.configuration.telegram_settings_manager import (
    TelegramSettingsManager
)
from modules.configuration.telegram_recipients_manager import (
    TelegramRecipientsManager
)
from modules.core.telegram_notification_queue import TelegramNotificationQueue

from modules.ui.roi_manager import ROIManager
from modules.ui.inspection.debug_dialog import DebugDialog
from modules.ui.inspection.log_viewer_dialog import LogViewerDialog

from modules.ui.inspection.controller_mixins.session_recovery_mixin import (
    SessionRecoveryMixin
)
from modules.ui.inspection.controller_mixins.telegram_mixin import (
    TelegramMixin
)
from modules.ui.inspection.controller_mixins.periodic_report_mixin import (
    PeriodicReportMixin
)
from modules.ui.inspection.controller_mixins.shift_tracking_mixin import (
    ShiftTrackingMixin
)
from modules.ui.inspection.controller_mixins.blur_detection_mixin import (
    BlurDetectionMixin
)
from modules.ui.inspection.controller_mixins.reference_age_mixin import (
    ReferenceAgeMixin
)
from modules.ui.inspection.controller_mixins.auto_backup_mixin import (
    AutoBackupMixin
)
from modules.ui.inspection.controller_mixins.data_retention_mixin import (
    DataRetentionMixin
)
from modules.ui.inspection.controller_mixins.marker_detection_mixin import (
    MarkerDetectionMixin
)
from modules.ui.inspection.controller_mixins.arduino_mixin import (
    ArduinoMixin
)
from modules.ui.inspection.controller_mixins.disk_space_mixin import (
    DiskSpaceMixin
)

from modules.controllers.inspection_controller import InspectionController
from modules.utils.logger import get_logger

app_logger = get_logger()


class InspectionUIController(
    SessionRecoveryMixin,
    TelegramMixin,
    PeriodicReportMixin,
    ShiftTrackingMixin,
    BlurDetectionMixin,
    ReferenceAgeMixin,
    AutoBackupMixin,
    DataRetentionMixin,
    MarkerDetectionMixin,
    ArduinoMixin,
    DiskSpaceMixin,
):
    """
    İnceleme (Inspection) ekranının ana orkestratörü: kamera/tick
    döngüsü, band/model seçimi, çoklu kamera kanalları ve arayüz
    kablolaması burada; NG bildirimi, vardiya takibi, bulanıklık,
    referans yaşı, otomatik yedekleme, veri saklama, ArUco marker
    tespiti, oturum
    toparlanma, Arduino ve disk alanı gibi kendi başına özellik
    grupları controller_mixins/ altındaki ayrı mixin sınıflarında.

    Her mixin, bu sınıfla aynı örneği (self) paylaştığından, burada
    tanımlı _throttled/_cooldown_ready gibi ortak yardımcılara ve
    __init__'te kurulan tüm manager/state alanlarına doğrudan erişir.
    """

    CAMERA_WIDTH = 1280
    CAMERA_HEIGHT = 720
    TIMER_INTERVAL_MS = 33

    CAMERA_FAILURE_THRESHOLD = 30
    RECONNECT_INTERVAL_SECONDS = 3.0

    def __init__(self, window, root=None, operator_name=None):

        self.window = window
        self.page = window.inspection_page
        self.operator_name = operator_name or "?"

        band_root = "configuration" if root is None else root / "configuration"

        self.band_manager = BandManager(root=band_root)
        self.model_manager = ModelManager()
        self.reference_manager = ReferenceManager()
        self.configuration_validator = ConfigurationValidator()
        self.telegram_settings_manager = TelegramSettingsManager(
            Path(band_root) / "telegram_settings.json"
        )
        self.telegram_recipients_manager = TelegramRecipientsManager(
            Path(band_root) / "telegram_recipients.json"
        )
        self.telegram_queue = TelegramNotificationQueue(
            Path(band_root) / "telegram_queue.json"
        )
        self._telegram_flush_thread = None
        self._last_telegram_flush_attempt = 0.0

        self._telegram_report_thread = None
        self._last_report_check_attempt = 0.0

        # Vardiya bazlı üretim sayacı (bkz. ShiftTrackingMixin). Aktif
        # pencere her kontrolde band.shifts'e göre yeniden hesaplanır,
        # ayrı bir "vardiya başladı" durumu tutulmaz.
        self._last_shift_check_attempt = 0.0

        # Kamera netliği (bulanıklık) takibi - bkz. BlurDetectionMixin.
        # Yanlış NG'lerin bir nedeni kamera odağı/lens kirliliği
        # olabileceğinden erkenden uyarır.
        self.blur_detector = BlurDetector()
        self.blur_streak = 0
        self._last_blur_check_attempt = 0.0
        self._last_blur_warning_at = None

        # Referans fotoğrafı yaşlanma hatırlatıcısı - bkz.
        # ReferenceAgeMixin.
        self._last_reference_age_check_attempt = 0.0
        self._last_reference_age_warning_at = None

        self.bands = []
        self.models = []

        self.current_band = None
        self.current_model = None

        self.recipe_manager = ModelRecipeAdapter(None)

        self.roi_manager = ROIManager()

        # Aynı kasayı ek açılardan izleyen kameralar (varsa).
        # channel_id -> {"channel", "roi_manager", "reference_image",
        #                "cap", "inspection_controller"}
        self.extra_channels = {}

        self.inspection_controller = None
        self.inspection_logger = None
        self.ng_capture_manager = NGCaptureManager()
        self.training_data_manager = TrainingDataManager()
        self.backup_manager = BackupManager()
        self.data_retention_manager = DataRetentionManager()

        self._backup_thread = None
        self._last_backup_check_attempt = 0.0
        self._data_retention_thread = None
        self._last_data_retention_check_attempt = 0.0
        self.unknown_kasa_capture_manager = UnknownKasaCaptureManager()

        # ArUco marker ile otomatik model tespiti - bkz.
        # MarkerDetectionMixin.
        self._marker_id_to_model = {}
        self._marker_detection_enabled = False
        self._pending_marker_candidate = None
        self._pending_marker_streak = 0
        self._last_unknown_marker_id_captured = None
        self._last_unknown_kasa_notified_at = None
        self.arduino_controller = None
        self.arduino_was_connected = True
        self.telegram_reaction_poller = None
        self.last_alert_state = None
        self.last_disk_check = 0.0
        self.disk_warning_active = False

        self.reference_image = None
        self.last_reference = None

        self.cap = None
        self.running = False

        self.camera_connected = True
        self.camera_failure_count = 0
        self.last_reconnect_attempt = 0.0

        self.last_arduino_reconnect_attempt = 0.0

        self.debug_enabled = False
        self.debug_dialog = None

        self.last_tick_time = None

        self.log_dialog = None

        self.timer = QTimer()
        self.timer.setInterval(self.TIMER_INTERVAL_MS)
        self.timer.timeout.connect(self._tick)

        self._connect_signals()

        self._load_bands()

        self.window.close_callback = self._on_window_closing

    # -------------------------------------------------
    # Periyodik Kontrol Yardımcıları (throttle / cooldown)
    # -------------------------------------------------
    #
    # Tick döngüsündeki neredeyse tüm "_maybe_*" kontrolleri (Telegram
    # kuyruğu, periyodik rapor, vardiya, bulanıklık, referans yaşı,
    # otomatik yedekleme, Arduino/kamera yeniden bağlanma, disk alanı)
    # aynı iki şekle sahiptir: (1) en fazla N saniyede bir çalışacak
    # bir kontrol, (2) zaten aktif bir uyarı durumunda bildirimi en
    # fazla N saniyede bir tekrarlayan bir "soğuma" süresi. Bu iki
    # yardımcı, o boilerplate'i tek satıra indirir - attribute adının
    # string olarak verilmesi, testlerin ilgili _last_* alanını
    # doğrudan (ör. controller._last_blur_check_attempt = 0.0) set
    # ederek throttle'ı manuel bypass edebilmesini korur.

    def _throttled(self, attr_name: str, interval_seconds: float) -> bool:

        now = time.perf_counter()

        if now - getattr(self, attr_name) < interval_seconds:
            return False

        setattr(self, attr_name, now)
        return True

    def _cooldown_ready(self, attr_name: str, cooldown_seconds: float) -> bool:

        last = getattr(self, attr_name)

        if (
            last is not None
            and time.perf_counter() - last < cooldown_seconds
        ):
            return False

        setattr(self, attr_name, time.perf_counter())
        return True

    # -------------------------------------------------
    # Pencere Kapanıyor
    # -------------------------------------------------

    def _on_window_closing(self):

        if self.running:
            self._stop()

        app_logger.info("[%s] çıkış yaptı (Inspection)", self.operator_name)

    # -------------------------------------------------
    # Sinyaller
    # -------------------------------------------------

    def _connect_signals(self):

        self.page.band_combo.currentIndexChanged.connect(
            self._on_band_changed
        )

        self.page.model_combo.currentIndexChanged.connect(
            self._on_model_changed
        )

        self.page.start_button.clicked.connect(
            self._on_start_clicked
        )

        self.page.save_reference_button.clicked.connect(
            self._on_save_reference_clicked
        )

        self.page.debug_button.clicked.connect(
            self._on_debug_clicked
        )

        self.page.history_button.clicked.connect(
            self._on_history_clicked
        )

    # -------------------------------------------------
    # Band / Model Yükleme
    # -------------------------------------------------
    #
    # Bilgisayar elektrik kesintisi/çökme sonrası yeniden açıldığında,
    # PIN girişi hâlâ gereklidir (güvenlik/hesap verebilirlik için) -
    # ama biri giriş yapar yapmaz, son kullanılan band/model otomatik
    # seçilir ve inceleme çalışıyor idiyse otomatik Başlat'a basılmış
    # gibi devam eder (bkz. SessionRecoveryMixin). "Çalışıyor idiyse"
    # hem gerçek bir çökmeyi hem de operatörün Durdur'a basmadan
    # pencereyi kapatmasını aynı şekilde ele alır - ikisini ayırt
    # etmek güvenilir değildir.

    def _load_bands(self):

        self.bands = self.band_manager.list_bands()

        self.page.set_band_list(
            [band.name for band in self.bands]
        )

        if not self.bands:
            self.page.set_status("Hiç band bulunamadı")
            return

        session_state = self._load_session_state()

        index = self._index_of_band_id(session_state["last_band_id"])

        if index is None:
            index = 0

        self.page.band_combo.blockSignals(True)
        self.page.band_combo.setCurrentIndex(index)
        self.page.band_combo.blockSignals(False)

        self._select_band(index)

        if session_state["was_running"]:
            self._start()

    def _select_band(self, index):

        if index < 0 or index >= len(self.bands):
            return

        self.current_band = self.bands[index]

        self._save_session_band()

        self._warn_if_band_config_invalid(self.current_band)

        self.inspection_logger = InspectionLogger(self.current_band)

        # Band değişince önceki bandın vardiya göstergesi anlamsız
        # kalır - bir sonraki kontrolde yeni bandın pencerelerine
        # göre yeniden hesaplanana kadar gizlenir.
        self.page.set_shift_progress(None)

        if self.debug_dialog is not None:
            self.debug_dialog.set_threshold(self.current_band.threshold)
            self.debug_dialog.set_confirm_frames(
                self.current_band.confirm_frames
            )
            self.debug_dialog.set_blur_threshold(
                self.current_band.blur_threshold
            )

        self.blur_streak = 0
        self._last_blur_warning_at = None

        self._last_reference_age_warning_at = None
        self.page.hide_reference_age_warning()

        self.roi_manager.load(self.current_band.roi)

        self.reference_image = self.reference_manager.load(
            self.current_band
        )

        self._load_extra_channels()

        self.models = self.model_manager.list_models(
            self.current_band
        )

        self._rebuild_marker_id_map()

        self.page.set_model_list(
            [model.name for model in self.models]
        )

        if self.models:

            session_state = self._load_session_state()

            model_index = self._index_of_model_id(
                session_state["last_model_id"]
            )

            if model_index is None:
                model_index = 0

            self.page.model_combo.blockSignals(True)
            self.page.model_combo.setCurrentIndex(model_index)
            self.page.model_combo.blockSignals(False)

            self._select_model(model_index)

        else:
            self.current_model = None
            self.recipe_manager = ModelRecipeAdapter(None)
            self._build_inspection_controller()

    def _load_extra_channels(self):
        """
        Bandın ek kamera kanallarını (varsa) yükler - her biri için
        kendi ROI setini ve referans fotoğrafını okur. Kameraları
        henüz AÇMAZ (birincil kamera gibi bu, _start()'ta olur).
        """

        for state in self.extra_channels.values():

            if state["cap"] is not None:
                state["cap"].release()

        self.extra_channels = {}

        for channel in self.current_band.cameras:

            roi_manager = ROIManager()
            roi_manager.load(channel.roi)

            self.extra_channels[channel.id] = {
                "channel": channel,
                "roi_manager": roi_manager,
                "reference_image": self.reference_manager.load(
                    channel.reference
                ),
                "cap": None,
                "inspection_controller": None
            }

    def _warn_if_band_config_invalid(self, band):

        result = self.configuration_validator.validate(band)

        if result["valid"]:
            return

        message = "\n".join(f"- {error}" for error in result["errors"])

        app_logger.warning(
            "[%s] '%s' bandı eksik/hatalı yapılandırmayla açıldı: %s",
            self.operator_name,
            band.name,
            "; ".join(result["errors"])
        )

        QMessageBox.warning(
            self.window,
            "Band Yapılandırması Eksik",
            f"'{band.name}' bandında şu sorunlar var:\n\n{message}\n\n"
            "İncelemeye başlamadan önce Kurulum'dan düzeltmeniz "
            "önerilir."
        )

    def _select_model(self, index):

        if index < 0 or index >= len(self.models):
            return

        self.current_model = self.models[index]

        self._save_session_model()

        self.recipe_manager = ModelRecipeAdapter(self.current_model)

        self._build_inspection_controller()

    # -------------------------------------------------
    # Eşik Ayarı (canlı, Debug ile birlikte ayarlanır)
    # -------------------------------------------------

    def _on_threshold_changed(self, value):

        if self.current_band is None:
            return

        self.current_band.threshold = value

        self.band_manager.save_band(self.current_band)

        if self.inspection_controller is not None:

            self.inspection_controller.inspection_processor.decision.set_threshold(
                value
            )

        app_logger.info(
            "[%s] eşik canlı değiştirildi: %s -> %%%.1f",
            self.operator_name,
            self.current_band.name,
            value
        )

    def _on_confirm_frames_changed(self, value):

        if self.current_band is None:
            return

        self.current_band.confirm_frames = value

        self.band_manager.save_band(self.current_band)

        if self.inspection_logger is not None:
            self.inspection_logger.set_confirm_frames(value)

        app_logger.info(
            "[%s] onay karesi sayısı canlı değiştirildi: %s -> %s",
            self.operator_name,
            self.current_band.name,
            value
        )

    def _on_blur_threshold_changed(self, value):

        if self.current_band is None:
            return

        self.current_band.blur_threshold = value

        self.band_manager.save_band(self.current_band)

        app_logger.info(
            "[%s] bulanıklık eşiği canlı değiştirildi: %s -> %.1f",
            self.operator_name,
            self.current_band.name,
            value
        )

    def _build_inspection_controller(self):

        decision_engine = DecisionEngine()

        if self.current_band is not None:
            decision_engine.set_threshold(self.current_band.threshold)

        self.inspection_controller = InspectionController(
            ArucoDetector(
                extra_valid_markers=self._marker_id_to_model.keys()
            ),
            LocalizationEngine(),
            ReferenceFrame(width=1200, height=800),
            InspectionEngine(),
            self.roi_manager,
            self.recipe_manager,
            decision_engine
        )

        for state in self.extra_channels.values():

            channel_decision_engine = DecisionEngine()

            if self.current_band is not None:
                channel_decision_engine.set_threshold(
                    self.current_band.threshold
                )

            state["inspection_controller"] = InspectionController(
                ArucoDetector(),
                LocalizationEngine(),
                ReferenceFrame(width=1200, height=800),
                InspectionEngine(),
                state["roi_manager"],
                PrefixedRecipeAdapter(
                    self.recipe_manager, state["channel"].name
                ),
                channel_decision_engine
            )

    # -------------------------------------------------
    # Combo Değişimi
    # -------------------------------------------------

    def _on_band_changed(self, index):

        if self.running:
            return

        self._select_band(index)

    def _on_model_changed(self, index):

        if self.running:
            return

        self._select_model(index)

    # -------------------------------------------------
    # Başlat / Durdur
    # -------------------------------------------------

    def _on_start_clicked(self):

        if self.running:
            self._stop()
        else:
            self._start()

    def _start(self):

        if self.current_band is None:

            QMessageBox.warning(
                self.window,
                "Uyarı",
                "Lütfen bir band seçin."
            )

            return

        self.cap = self._open_camera(self.current_band.camera)

        if self.cap is None:

            QMessageBox.warning(
                self.window,
                "Hata",
                "Kamera açılamadı."
            )

            return

        self._open_extra_channel_cameras()

        self._build_inspection_controller()

        self._connect_arduino()
        self._start_telegram_reaction_poller()

        self.running = True
        self.camera_connected = True
        self.camera_failure_count = 0

        self._save_session_running(True)

        self.page.set_start_button_text("&Durdur")
        self.page.enable_selection(False)
        self.page.set_status("BAĞLANDI")

        self.last_tick_time = time.perf_counter()

        self.timer.start()

    def _open_camera(self, camera_index):

        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.CAMERA_HEIGHT)

        if not cap.isOpened():
            cap.release()
            return None

        return cap

    def _open_extra_channel_cameras(self):
        """
        Ek kamera kanallarının her birini açmayı dener. Biri
        açılamazsa incelemeyi durdurmaz - o kanal sadece bu oturum
        boyunca sonuçsuz kalır (tick döngüsü cap=None olan kanalları
        atlar), diğer kanallar/birincil kamera etkilenmez.
        """

        for state in self.extra_channels.values():

            cap = self._open_camera(state["channel"].camera_index)

            state["cap"] = cap

            if cap is None:

                app_logger.warning(
                    "Ek kamera açılamadı: %s (index=%s)",
                    state["channel"].name,
                    state["channel"].camera_index
                )

    # -------------------------------------------------
    # Kamera Bağlantısı Koptu / Yeniden Bağlan
    # -------------------------------------------------

    def _handle_camera_disconnected(self):

        band_name = (
            self.current_band.name
            if self.current_band is not None
            else "?"
        )

        app_logger.error(
            "Kamera bağlantısı koptu (band=%s)",
            band_name
        )

        self._notify_telegram_disconnect("Kamera")

        self.camera_connected = False
        self.last_reconnect_attempt = time.perf_counter()

        if self.cap is not None:
            self.cap.release()
            self.cap = None

        self.page.set_status(
            "Kamera bağlantısı koptu, yeniden bağlanılıyor..."
        )

    def _attempt_camera_reconnect(self):

        if not self._throttled(
            "last_reconnect_attempt", self.RECONNECT_INTERVAL_SECONDS
        ):
            return

        camera_index = (
            self.current_band.camera
            if self.current_band is not None
            else 0
        )

        cap = self._open_camera(camera_index)

        if cap is None:

            self.page.set_status(
                "Kamera bağlantısı koptu, yeniden bağlanılıyor..."
            )

            return

        self.cap = cap
        self.camera_connected = True
        self.camera_failure_count = 0

        app_logger.info(
            "Kamera yeniden bağlandı (band=%s)",
            self.current_band.name if self.current_band is not None else "?"
        )

        self.page.set_status("Kamera yeniden bağlandı - BAĞLANDI")

    def _stop(self):

        self.timer.stop()

        self._stop_telegram_reaction_poller()

        if self.cap is not None:
            self.cap.release()
            self.cap = None

        for state in self.extra_channels.values():

            if state["cap"] is not None:
                state["cap"].release()
                state["cap"] = None

        if self.arduino_controller is not None:

            # Kapatmadan önce Arduino'yu bekleme durumuna resetle -
            # aksi halde Arduino son NG/OK durumunu (buzzer/LED/LCD)
            # süresiz göstermeye devam eder. "OK" göndermiyoruz çünkü
            # durdurulduğunda aslında hiçbir şey incelenmiyor.
            self.arduino_controller.send_waiting()

            self.arduino_controller.close()
            self.arduino_controller = None

        self.running = False
        self.camera_connected = True
        self.camera_failure_count = 0

        self._save_session_running(False)

        self.page.set_start_button_text("&Başlat")
        self.page.enable_selection(True)
        self.page.set_status("Durduruldu")
        self.page.clear_image()
        self.page.clear_results()
        self.page.hide_ng_alert()
        self.page.hide_blur_warning()
        self.blur_streak = 0
        self.last_alert_state = None

        if self.debug_dialog is not None:
            self.debug_dialog.hide()
            self.debug_enabled = False
            self.page.set_debug_button_text("&Hata Ayıklama Göster")

    # -------------------------------------------------
    # Reference Kaydet
    # -------------------------------------------------

    def _on_save_reference_clicked(self):

        if self.current_band is None or self.last_reference is None:

            QMessageBox.warning(
                self.window,
                "Uyarı",
                "Kaydedilecek bir referans görüntüsü yok."
            )

            return

        self.reference_manager.save(
            self.current_band,
            self.last_reference
        )

        self.reference_image = self.reference_manager.load(
            self.current_band
        )

        QMessageBox.information(
            self.window,
            "Başarılı",
            "Referans güncellendi."
        )

    # -------------------------------------------------
    # Debug Göster / Gizle
    # -------------------------------------------------

    def _on_debug_clicked(self):

        if self.debug_dialog is None:

            self.debug_dialog = DebugDialog(self.window)

            if self.current_band is not None:
                self.debug_dialog.set_threshold(self.current_band.threshold)
                self.debug_dialog.set_confirm_frames(
                    self.current_band.confirm_frames
                )
                self.debug_dialog.set_blur_threshold(
                    self.current_band.blur_threshold
                )

            self.debug_dialog.threshold_spinbox.valueChanged.connect(
                self._on_threshold_changed
            )

            self.debug_dialog.confirm_frames_spinbox.valueChanged.connect(
                self._on_confirm_frames_changed
            )

            self.debug_dialog.blur_threshold_spinbox.valueChanged.connect(
                self._on_blur_threshold_changed
            )

            self.debug_dialog.finished.connect(self._on_debug_dialog_closed)

            self.debug_dialog.show()

            self.debug_enabled = True
            self.page.set_debug_button_text("&Hata Ayıklama Gizle")

            return

        if self.debug_dialog.isVisible():
            self.debug_dialog.hide()
            self.debug_enabled = False
            self.page.set_debug_button_text("&Hata Ayıklama Göster")
        else:
            self.debug_dialog.show()
            self.debug_enabled = True
            self.page.set_debug_button_text("&Hata Ayıklama Gizle")

    def _on_debug_dialog_closed(self):

        self.debug_enabled = False
        self.page.set_debug_button_text("&Hata Ayıklama Göster")

    # -------------------------------------------------
    # Geçmiş
    # -------------------------------------------------

    def _on_history_clicked(self):

        if self.inspection_logger is None or self.current_band is None:

            QMessageBox.warning(
                self.window,
                "Uyarı",
                "Önce bir band seçin."
            )

            return

        if self.log_dialog is not None:

            self.log_dialog.reload()
            self.log_dialog.show()
            self.log_dialog.raise_()
            self.log_dialog.activateWindow()
            return

        self.log_dialog = LogViewerDialog(
            self.inspection_logger,
            self.current_band.name,
            self.window,
            operator_name=self.operator_name,
            band=self.current_band
        )

        self.log_dialog.finished.connect(self._on_history_closed)

        self.log_dialog.clear_button.clicked.connect(
            self._on_clear_history_clicked
        )

        self.log_dialog.show()

    def _on_history_closed(self):

        self.log_dialog = None

    def _on_clear_history_clicked(self):

        answer = QMessageBox.question(
            self.window,
            "Emin misiniz?",
            "Bu bandın tüm inceleme geçmişi ve hata fotoğrafları "
            "silinecek. Devam edilsin mi?"
        )

        if answer != QMessageBox.Yes:
            return

        self.inspection_logger.clear()
        self.ng_capture_manager.clear(self.current_band)

        app_logger.info(
            "[%s] inspection geçmişi temizlendi: %s",
            self.operator_name,
            self.current_band.name if self.current_band is not None else "?"
        )

        if self.log_dialog is not None:
            self.log_dialog.reload()

        QMessageBox.information(
            self.window,
            "Başarılı",
            "Geçmiş temizlendi."
        )

    # -------------------------------------------------
    # NG Uyarısı
    # -------------------------------------------------

    def _update_ng_alert(self, overall_result):

        if overall_result == "NG":

            self.page.show_ng_alert()

            if self.last_alert_state != "NG":

                winsound.MessageBeep(winsound.MB_ICONHAND)

        else:

            self.page.hide_ng_alert()

        self.last_alert_state = overall_result

    # -------------------------------------------------
    # Ek Kamera Kanalları (aynı kasayı farklı açıdan izleyen kameralar)
    # -------------------------------------------------

    def _build_combined_results_and_display(self, primary_results, primary_display):
        """
        Birincil kameranın sonuçlarına/görüntüsüne, varsa ek kamera
        kanallarının sonuçlarını/görüntülerini ekler.

        Ek kanalların ROI isimleri "KanalAdı:ROI" şeklinde nitelenir
        ki iki farklı kanalda aynı isimde (ör. "G01") bir ROI olsa
        bile karışmasın. Genel OK/NG kararı, tüm kanalların TÜM
        gözlerinin birleşiminden hesaplanır (herhangi biri NG ise
        genel sonuç NG).

        Bir kanalın kamerası açılamadıysa veya o kare okunamadıysa,
        o kanal sessizce atlanır - diğer kanallar/birincil kamera
        etkilenmez.
        """

        combined_results = dict(primary_results)
        combined_display = primary_display

        for state in self.extra_channels.values():

            if state["cap"] is None:
                continue

            ret, frame = state["cap"].read()

            if not ret:
                continue

            channel_result = state["inspection_controller"].process(
                frame, state["reference_image"]
            )

            if not channel_result["success"]:
                continue

            channel_display = channel_result["reference_display"]

            if channel_display is None:
                channel_display = frame

            combined_display = self._hconcat_images(
                combined_display, channel_display
            )

            channel_name = state["channel"].name

            for roi_name, data in channel_result["results"].items():
                combined_results[f"{channel_name}:{roi_name}"] = data

        return combined_results, combined_display

    def _hconcat_images(self, left, right):

        height = min(left.shape[0], right.shape[0])

        left_resized = cv2.resize(
            left,
            (int(left.shape[1] * height / left.shape[0]), height)
        )

        right_resized = cv2.resize(
            right,
            (int(right.shape[1] * height / right.shape[0]), height)
        )

        return cv2.hconcat([left_resized, right_resized])

    # -------------------------------------------------
    # Kamera Döngüsü
    # -------------------------------------------------

    def _save_training_images(self, combined_results, debug) -> dict:
        """
        debug (result["debug"]) sadece BİRİNCİL kameranın ROI'lerini
        içerir, ham (nitelenmemiş) isimlerle anahtarlanır - bu yüzden
        v1 kapsamı sadece birincil kameradır (ek kamera kanallarının
        debug verisi şu an _tick_impl'e hiç ulaşmıyor). Her ROI için
        referans/canlı kırpmasını, o anki görsel duruma (DOLU/BOŞ)
        göre TrainingDataManager ile diske kaydeder.
        """

        if not debug:
            return {}

        training_image_paths = {}

        for roi_name, compare in debug.items():

            roi_data = combined_results.get(roi_name)

            if roi_data is None:
                continue

            saved = self.training_data_manager.save(
                self.current_band,
                roi_name,
                roi_data["state"],
                compare.get("reference"),
                compare.get("current")
            )

            if saved is not None:
                training_image_paths[roi_name] = saved

        return training_image_paths

    def _tick(self):

        try:

            self._tick_impl()

        except Exception:

            app_logger.exception(
                "Inspection tick sırasında beklenmeyen hata"
            )

            self.page.set_status(
                "Beklenmeyen hata oluştu (bkz. logs/app.log)"
            )

    def _tick_impl(self):

        self._check_disk_space()
        self._maybe_flush_telegram_queue()
        self._maybe_send_periodic_report()
        self._maybe_check_shift_progress()
        self._maybe_check_reference_age()
        self._maybe_run_auto_backup()
        self._maybe_run_data_retention()

        if self.arduino_controller is not None:

            if self.arduino_controller.is_connected():

                self.arduino_was_connected = True

            else:

                if self.arduino_was_connected:

                    app_logger.error("Arduino bağlantısı koptu")
                    self._notify_telegram_disconnect("Arduino")

                self.arduino_was_connected = False

                self._attempt_arduino_reconnect()

        if not self.camera_connected:
            self._attempt_camera_reconnect()
            return

        if self.cap is None:
            return

        ret, frame = self.cap.read()

        if not ret:

            self.camera_failure_count += 1

            if self.camera_failure_count >= self.CAMERA_FAILURE_THRESHOLD:
                self._handle_camera_disconnected()

            return

        self.camera_failure_count = 0

        self._maybe_check_blur(frame)

        result = self.inspection_controller.process(
            frame,
            self.reference_image
        )

        now = time.perf_counter()

        elapsed = now - self.last_tick_time

        self.last_tick_time = now

        fps = 1 / elapsed if elapsed > 0 else 0

        inspection_time = elapsed * 1000

        if not result["success"]:

            self.page.set_status(f"Hata: {result['error']}")

            return

        self.last_reference = result["reference"]

        is_unknown_kasa_frame = False

        if self._marker_detection_enabled:
            is_unknown_kasa_frame = self._handle_marker_model_detection(
                result
            )

        display = result["reference_display"]

        if display is None:
            display = frame

        combined_results, display = self._build_combined_results_and_display(
            result["results"], display
        )

        self.page.set_image(display)

        self.page.set_results(combined_results)

        overall_result = None

        if combined_results:

            overall_result = (
                "OK"
                if all(data["ok"] for data in combined_results.values())
                else "NG"
            )

        self._update_ng_alert(overall_result)

        if self.arduino_controller is not None:

            if combined_results:
                self.arduino_controller.send_results(combined_results)
            else:
                self.arduino_controller.send_waiting()

        if (
            self.inspection_logger is not None
            and combined_results
            and not is_unknown_kasa_frame
            and self.inspection_logger.should_log(combined_results)
        ):

            model_name = (
                self.current_model.name
                if self.current_model is not None
                else None
            )

            image_path = None

            if overall_result == "NG":

                image_path = self.ng_capture_manager.save(
                    self.current_band,
                    display
                )

            training_image_paths = None

            if self.current_band.training_data_collection_enabled:

                training_image_paths = self._save_training_images(
                    combined_results, result.get("debug")
                )

            self.inspection_logger.log(
                combined_results,
                model_name,
                image_path,
                training_image_paths
            )

            if overall_result == "NG":

                self._notify_telegram_ng(
                    combined_results,
                    image_path,
                    self.inspection_logger.last_inserted_id
                )

        localization = result["localization"]

        if localization is not None:

            mode_text = localization["mode"]

            if (
                mode_text == "NORMAL"
                and not localization.get("settled", True)
            ):
                mode_text += " (kalibre ediliyor)"

            self.page.set_mode(mode_text)
            self.page.set_confidence(localization["confidence"])

        self.page.set_performance(fps, inspection_time)

        if result["results"]:
            self.page.set_status("BAĞLANDI")
        else:
            self.page.set_status("Kamera bekleniyor / Parça yok")

        if self.debug_enabled and self.debug_dialog is not None:

            self.debug_dialog.show_debug(result["debug"])
