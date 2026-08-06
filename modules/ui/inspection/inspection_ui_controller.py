import time
import threading
import winsound
from datetime import datetime, timezone, timedelta
from pathlib import Path

import cv2

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox

from modules.core.aruco_detector import ArucoDetector
from modules.core.localization import LocalizationEngine
from modules.core.reference_frame import ReferenceFrame
from modules.core.inspection_engine import InspectionEngine
from modules.core.decision_engine import DecisionEngine
from modules.core.arduino_controller import ArduinoController
from modules.core.telegram_notifier import TelegramNotifier
from modules.core.telegram_reaction_poller import TelegramReactionPoller
from modules.core.telegram_notification_queue import (
    TelegramNotificationQueue,
    QueuedNotification
)
from modules.configuration.periodic_report_exporter import (
    PeriodicReportExporter
)
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

from modules.ui.roi_manager import ROIManager
from modules.ui.inspection.debug_dialog import DebugDialog
from modules.ui.inspection.log_viewer_dialog import LogViewerDialog
from modules.ui.window_utils import get_app_settings

from modules.controllers.inspection_controller import InspectionController
from modules.utils.logger import get_logger
from modules.utils.disk_monitor import get_free_space_gb

app_logger = get_logger()


class InspectionUIController:

    CAMERA_WIDTH = 1280
    CAMERA_HEIGHT = 720
    TIMER_INTERVAL_MS = 33

    CAMERA_FAILURE_THRESHOLD = 30
    RECONNECT_INTERVAL_SECONDS = 3.0

    ARDUINO_RECONNECT_INTERVAL_SECONDS = 5.0

    # Kuyruktaki gönderilemeyen Telegram bildirimlerini tekrar
    # deneme sıklığı. Çok sık denemek (ör. her karede) bağlantı
    # koptuğunda Telegram'a gereksiz yük bindirir.
    TELEGRAM_QUEUE_FLUSH_INTERVAL_SECONDS = 60.0

    # Periyodik özet raporunun ne sıklıkla gönderileceğinin ("her 24
    # saatte bir") ve bunun ne sıklıkla kontrol edileceğinin
    # (5 dakikada bir - saatlik hassasiyet yeterli, her karede
    # kontrol etmeye gerek yok) ayarları.
    REPORT_PERIOD_HOURS = 24
    REPORT_CHECK_INTERVAL_SECONDS = 300.0

    # Vardiya ilerlemesinin ne sıklıkla kontrol edileceği, ne kadar
    # geride kalmanın "normal" sayılacağı (kasa değişim süresi vb.
    # doğal dalgalanmalar için pay) ve aynı vardiyada bildirimler
    # arasında en az ne kadar süre olması gerektiği.
    SHIFT_CHECK_INTERVAL_SECONDS = 60.0
    SHIFT_PACE_TOLERANCE = 0.2
    SHIFT_WARNING_COOLDOWN_SECONDS = 3600.0

    # Bulanıklık kontrolünün sıklığı, kaç ardışık kontrolün "sürekli
    # bulanık" saymak için gerektiği (tek kötü kare/geçici titreme
    # için uyarmasın diye) ve aynı bağlantı için bildirimler arası
    # minimum süre.
    BLUR_CHECK_INTERVAL_SECONDS = 2.0
    BLUR_STREAK_THRESHOLD = 3
    BLUR_WARNING_COOLDOWN_SECONDS = 300.0

    # Referans yaşı gün hassasiyetinde değiştiğinden sık kontrole
    # gerek yok; hatırlatma da günde bir defadan fazla tekrar etmesin.
    REFERENCE_AGE_CHECK_INTERVAL_SECONDS = 3600.0
    REFERENCE_AGE_WARNING_COOLDOWN_SECONDS = 86400.0

    # Otomatik yedeklemenin gerçek sıklığı band.auto_backup_interval_hours
    # ile belirlenir - bu sadece o kontrolün ne sıklıkla yapılacağı
    # (saatlik kontrol, dakikalık hassasiyete gerek yok).
    BACKUP_CHECK_INTERVAL_SECONDS = 3600.0

    # Son kullanılan band/model/çalışma durumunu makine ayarlarında
    # (window_settings.ini) saklamak için kullanılan anahtar öneki -
    # bkz. _save_session_band/_save_session_model/_save_session_running,
    # otomatik toparlanma (crash/elektrik kesintisi sonrası).
    SESSION_SETTINGS_KEY = "inspection_session"

    # ArUco marker ile otomatik model tespiti: yanlış okumadan (tek
    # kare titremesi) dolayı model aniden değişmesin diye aynı
    # marker ID'sinin bu kadar ardışık karede görülmesi gerekir.
    # Tanınmayan kasa bildirimleri de en fazla bu sıklıkta tekrarlar.
    MARKER_SWITCH_CONFIRM_FRAMES = 5
    UNKNOWN_KASA_NOTIFY_COOLDOWN_SECONDS = 300.0

    DISK_WARNING_THRESHOLD_GB = 5.0
    DISK_CHECK_INTERVAL_SECONDS = 60.0

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

        # Vardiya bazlı üretim takibi (bkz. _maybe_check_shift_progress).
        # shift_start_time, _start() ilk çağrıldığında (ya da band
        # değiştiğinde) ayarlanır; band.shift_target_count == 0 ise
        # tüm takip/uyarı devre dışı kalır.
        self.shift_start_time = None
        self._last_shift_check_attempt = 0.0
        self._last_shift_warning_at = None

        # Kamera netliği (bulanıklık) takibi - bkz.
        # _maybe_check_blur. Yanlış NG'lerin bir nedeni kamera odağı/
        # lens kirliliği olabileceğinden erkenden uyarır.
        self.blur_detector = BlurDetector()
        self.blur_streak = 0
        self._last_blur_check_attempt = 0.0
        self._last_blur_warning_at = None

        # Referans fotoğrafı yaşlanma hatırlatıcısı - bkz.
        # _maybe_check_reference_age.
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

        self._backup_thread = None
        self._last_backup_check_attempt = 0.0
        self.unknown_kasa_capture_manager = UnknownKasaCaptureManager()

        # ArUco marker ile otomatik model tespiti - bkz.
        # _rebuild_marker_id_map / _handle_marker_model_detection.
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
    # Oturum Durumu (Otomatik Toparlanma)
    # -------------------------------------------------
    #
    # Bilgisayar elektrik kesintisi/çökme sonrası yeniden açıldığında,
    # PIN girişi hâlâ gereklidir (güvenlik/hesap verebilirlik için) -
    # ama biri giriş yapar yapmaz, son kullanılan band/model otomatik
    # seçilir ve inceleme çalışıyor idiyse otomatik Başlat'a basılmış
    # gibi devam eder. "Çalışıyor idiyse" hem gerçek bir çökmeyi hem
    # de operatörün Durdur'a basmadan pencereyi kapatmasını aynı
    # şekilde ele alır - ikisini ayırt etmek güvenilir değildir.

    def _save_session_band(self):

        settings = get_app_settings()

        settings.setValue(
            f"{self.SESSION_SETTINGS_KEY}/last_band_id",
            self.current_band.id if self.current_band is not None else None
        )

    def _save_session_model(self):

        settings = get_app_settings()

        settings.setValue(
            f"{self.SESSION_SETTINGS_KEY}/last_model_id",
            self.current_model.id
            if self.current_model is not None else None
        )

    def _save_session_running(self, running: bool):

        settings = get_app_settings()

        settings.setValue(
            f"{self.SESSION_SETTINGS_KEY}/was_running", running
        )

    def _load_session_state(self) -> dict:

        settings = get_app_settings()

        return {
            "last_band_id": settings.value(
                f"{self.SESSION_SETTINGS_KEY}/last_band_id", None
            ),
            "last_model_id": settings.value(
                f"{self.SESSION_SETTINGS_KEY}/last_model_id", None
            ),
            "was_running": settings.value(
                f"{self.SESSION_SETTINGS_KEY}/was_running",
                False,
                type=bool
            )
        }

    def _index_of_band_id(self, band_id):

        if band_id is None:
            return None

        for index, band in enumerate(self.bands):

            if band.id == band_id:
                return index

        return None

    def _index_of_model_id(self, model_id):

        if model_id is None:
            return None

        for index, model in enumerate(self.models):

            if model.id == model_id:
                return index

        return None

    # -------------------------------------------------
    # Band / Model Yükleme
    # -------------------------------------------------

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

        # Band değişince önceki bandın vardiya ilerlemesi anlamsız
        # kalır - yeni band seçilince sıfırdan başlar.
        self.shift_start_time = None
        self._last_shift_warning_at = None
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

    def _rebuild_marker_id_map(self):
        """
        Bandın modellerinden marker_id -> Model haritasını kurar.
        Hiçbir modelde marker_id ayarlanmamışsa (eski/tek modelli
        bandlar) tespit tamamen devre dışı kalır - sıfır davranış
        değişikliği.
        """

        self._marker_id_to_model = {
            model.marker_id: model for model in self.models
            if model.marker_id is not None
        }

        self._marker_detection_enabled = bool(self._marker_id_to_model)
        self._pending_marker_candidate = None
        self._pending_marker_streak = 0
        self._last_unknown_marker_id_captured = None

        self.page.hide_unknown_kasa_warning()

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
            "İncelemeye başlamadan önce Configurator'dan düzeltmeniz "
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

        # Vardiya, bu banda ilk kez Başlat'a basıldığında başlar.
        # Aynı vardiya içinde durdurup tekrar başlatmak ilerlemeyi
        # sıfırlamaz (kısa bir mola vardiyayı bitirmez).
        if self.shift_start_time is None:
            self.shift_start_time = datetime.now(timezone.utc)

        self.running = True
        self.camera_connected = True
        self.camera_failure_count = 0

        self._save_session_running(True)

        self.page.set_start_button_text("&Durdur")
        self.page.enable_selection(False)
        self.page.set_status("CONNECTED")

        self.last_tick_time = time.perf_counter()

        self.timer.start()

    # -------------------------------------------------
    # Telegram Bildirimleri
    # -------------------------------------------------

    def _telegram_chat_ids(self, primary_chat_id: str) -> list:
        """
        Bildirimin gideceği tüm chat id'ler: birincil (ayarlardaki
        tek) chat + telefon numarasıyla kaydolmuş, aktif işaretli
        tüm alıcılar. Tekrarlar elenir.
        """

        chat_ids = []

        if primary_chat_id.strip():
            chat_ids.append(primary_chat_id.strip())

        for chat_id in self.telegram_recipients_manager.active_chat_ids():

            if chat_id not in chat_ids:
                chat_ids.append(chat_id)

        return chat_ids

    def _notify_telegram_ng(self, results: dict, image_path, record_id):

        settings = self.telegram_settings_manager.load()

        if not settings.notify_on_ng or not settings.bot_token.strip():
            return

        chat_ids = self._telegram_chat_ids(settings.chat_id)

        if not chat_ids:
            return

        ng_names = [
            name for name, data in results.items()
            if not data.get("ok", True)
        ]

        band_name = (
            self.current_band.name
            if self.current_band is not None
            else "?"
        )

        caption = (
            f"⚠ NG - {band_name}\n"
            f"Hatalı gözler: {', '.join(ng_names) if ng_names else '-'}"
        )

        if settings.react_to_confirm:

            caption += (
                f"\n\nYanlış tespitse bu mesaja {settings.confirm_emoji} "
                "ile tepki verin, otomatik olarak OK'e çevrilir."
            )

        # inspection_logger band değişse bile DOĞRU kayda yazsın diye
        # şu anki referansı closure içine sabitliyoruz (arka plan
        # thread'i mesaj gönderimi bitince çalışır, o ana kadar band
        # değişmiş/durdurulmuş olabilir).
        logger_at_send_time = self.inspection_logger

        def on_primary_success(message_id):

            # Emoji ile onaylama sadece BİRİNCİL sohbetteki mesaj
            # için destekleniyor (her alıcının kendi mesaj id'sini
            # ayrı ayrı izlemek şimdilik kapsam dışı).
            if record_id is not None and logger_at_send_time is not None:
                logger_at_send_time.set_telegram_message_id(
                    record_id, message_id
                )

        for index, chat_id in enumerate(chat_ids):

            notifier = TelegramNotifier(settings.bot_token, chat_id)

            is_primary = index == 0

            callback = self._telegram_retry_on_failure_callback(
                kind="photo" if image_path else "message",
                bot_token=settings.bot_token,
                chat_id=chat_id,
                text=caption,
                image_path=str(image_path) if image_path else "",
                record_id=record_id,
                is_primary=is_primary,
                on_success=on_primary_success if is_primary else None
            )

            if image_path:
                notifier.send_photo_async(
                    image_path, caption=caption, on_sent=callback
                )
            else:
                notifier.send_message_async(caption, on_sent=callback)

    def _telegram_retry_on_failure_callback(
        self,
        kind,
        bot_token,
        chat_id,
        text,
        image_path="",
        record_id=None,
        is_primary=False,
        on_success=None
    ):
        """
        Gönderim başarılıysa (varsa) on_success(message_id) çağırır.
        Başarısızsa - ağ/Telegram erişilemiyorsa - bildirimi kuyruğa
        ekler ki bağlantı geri geldiğinde tekrar denensin (bkz.
        _maybe_flush_telegram_queue).
        """

        def on_sent(message_id):

            if message_id is not None:

                if on_success is not None:
                    on_success(message_id)

                return

            self.telegram_queue.enqueue(QueuedNotification(
                kind=kind,
                bot_token=bot_token,
                chat_id=chat_id,
                text=text,
                image_path=image_path,
                record_id=record_id,
                is_primary=is_primary
            ))

        return on_sent

    def _notify_telegram_disconnect(self, device_name: str):

        settings = self.telegram_settings_manager.load()

        if not settings.notify_on_disconnect or not settings.bot_token.strip():
            return

        chat_ids = self._telegram_chat_ids(settings.chat_id)

        if not chat_ids:
            return

        band_name = (
            self.current_band.name
            if self.current_band is not None
            else "?"
        )

        text = f"🔌 {device_name} bağlantısı koptu - {band_name}"

        for chat_id in chat_ids:

            callback = self._telegram_retry_on_failure_callback(
                kind="message",
                bot_token=settings.bot_token,
                chat_id=chat_id,
                text=text
            )

            TelegramNotifier(
                settings.bot_token, chat_id
            ).send_message_async(text, on_sent=callback)

    # -------------------------------------------------
    # Telegram Bildirim Kuyruğunu Boşaltma
    # -------------------------------------------------

    def _maybe_flush_telegram_queue(self):
        """
        Ağ/Telegram erişilemediği için kuyruğa düşmüş bildirimleri
        tekrar göndermeyi dener. Her karede değil, en fazla
        TELEGRAM_QUEUE_FLUSH_INTERVAL_SECONDS'te bir - aksi halde
        bağlantı koptuğunda Telegram'a saniyede onlarca istek atılır.
        Ağ isteği içerdiğinden her zaman arka plan thread'inde çalışır.
        """

        now = time.perf_counter()

        if (
            now - self._last_telegram_flush_attempt
            < self.TELEGRAM_QUEUE_FLUSH_INTERVAL_SECONDS
        ):
            return

        if (
            self._telegram_flush_thread is not None
            and self._telegram_flush_thread.is_alive()
        ):
            return

        self._last_telegram_flush_attempt = now

        logger_at_flush_time = self.inspection_logger

        def on_message_sent(record_id, message_id):

            if record_id is not None and logger_at_flush_time is not None:
                logger_at_flush_time.set_telegram_message_id(
                    record_id, message_id
                )

        def _run():

            sent_count = self.telegram_queue.flush(
                notifier_factory=TelegramNotifier,
                on_message_sent=on_message_sent
            )

            if sent_count:

                app_logger.info(
                    "Kuyruktaki %d Telegram bildirimi gönderildi.",
                    sent_count
                )

        self._telegram_flush_thread = threading.Thread(
            target=_run, daemon=True
        )
        self._telegram_flush_thread.start()

    # -------------------------------------------------
    # Periyodik Özet Rapor
    # -------------------------------------------------

    def _resolve_report_period_start(self, settings, now_utc):
        """
        Son rapor ne zaman gönderildiyse ondan bu yana geçen süreye
        bakar. REPORT_PERIOD_HOURS dolmadıysa None döner (henüz
        rapor zamanı değil). Hiç gönderilmemişse ya da tarih
        okunamıyorsa, son REPORT_PERIOD_HOURS'u kapsayan bir rapor
        için başlangıç noktası döner.
        """

        if not settings.last_daily_report_sent_at:
            return now_utc - timedelta(hours=self.REPORT_PERIOD_HOURS)

        try:
            last_sent = datetime.fromisoformat(
                settings.last_daily_report_sent_at
            )
        except Exception:
            return now_utc - timedelta(hours=self.REPORT_PERIOD_HOURS)

        elapsed_hours = (now_utc - last_sent).total_seconds() / 3600

        if elapsed_hours < self.REPORT_PERIOD_HOURS:
            return None

        return last_sent

    def _maybe_send_periodic_report(self):
        """
        Ayarlarda açıksa, her REPORT_PERIOD_HOURS saatte bir bandın
        toplam/OK/NG ve model/ROI bazlı özetini bir Excel dosyası
        olarak Telegram'a gönderir. Gönderim başarısız olursa (ağ
        kopuksa) diğer bildirimlerle aynı kuyruğa (telegram_queue)
        eklenir - kaybolmaz, bağlantı gelince tekrar denenir.
        """

        now = time.perf_counter()

        if (
            now - self._last_report_check_attempt
            < self.REPORT_CHECK_INTERVAL_SECONDS
        ):
            return

        self._last_report_check_attempt = now

        if self.inspection_logger is None or self.current_band is None:
            return

        settings = self.telegram_settings_manager.load()

        if not settings.daily_report_enabled or not settings.is_configured():
            return

        now_utc = datetime.now(timezone.utc)

        since = self._resolve_report_period_start(settings, now_utc)

        if since is None:
            return

        if (
            self._telegram_report_thread is not None
            and self._telegram_report_thread.is_alive()
        ):
            return

        band = self.current_band
        logger_at_send_time = self.inspection_logger
        chat_ids = self._telegram_chat_ids(settings.chat_id)

        def _run():

            stats = logger_at_send_time.compute_period_stats(
                since.isoformat()
            )

            reports_folder = band.root / "telegram_reports"
            reports_folder.mkdir(parents=True, exist_ok=True)

            report_path = reports_folder / (
                f"rapor_{now_utc.strftime('%Y%m%d_%H%M%S')}.xlsx"
            )

            PeriodicReportExporter().export(
                stats, report_path, band.name, "Son 24 Saat Özeti"
            )

            caption = (
                f"📊 Günlük Özet - {band.name}\n"
                f"Toplam: {stats['total']} | OK: {stats['ok_count']} | "
                f"NG: {stats['ng_count']}"
            )

            for chat_id in chat_ids:

                notifier = TelegramNotifier(settings.bot_token, chat_id)

                message_id = notifier.send_document(
                    str(report_path), caption=caption
                )

                if message_id is None:

                    self.telegram_queue.enqueue(QueuedNotification(
                        kind="document",
                        bot_token=settings.bot_token,
                        chat_id=chat_id,
                        text=caption,
                        image_path=str(report_path)
                    ))

            updated_settings = self.telegram_settings_manager.load()
            updated_settings.last_daily_report_sent_at = (
                now_utc.isoformat()
            )
            self.telegram_settings_manager.save(updated_settings)

        self._telegram_report_thread = threading.Thread(
            target=_run, daemon=True
        )
        self._telegram_report_thread.start()

    # -------------------------------------------------
    # Vardiya Bazlı Üretim Takibi
    # -------------------------------------------------

    def _maybe_check_shift_progress(self):
        """
        Bandın vardiya hedefi tanımlıysa (shift_target_count > 0),
        vardiya başlangıcından bu yana kaç kasa incelendiğini
        (InspectionLogger'a düşen kayıt sayısı - compute_period_stats
        ile aynı sorgu, periyodik rapor özelliğiyle paylaşılıyor)
        hesaplar, arayüzde gösterir ve beklenen tempoya göre
        ciddi şekilde geride kalınmışsa Telegram'dan uyarır.
        """

        now = time.perf_counter()

        if (
            now - self._last_shift_check_attempt
            < self.SHIFT_CHECK_INTERVAL_SECONDS
        ):
            return

        self._last_shift_check_attempt = now

        if self.current_band is None or self.inspection_logger is None:
            return

        if self.shift_start_time is None:
            return

        target = self.current_band.shift_target_count

        if target <= 0:
            self.page.set_shift_progress(None)
            return

        duration_hours = self.current_band.shift_duration_hours

        now_utc = datetime.now(timezone.utc)

        elapsed_hours = (
            (now_utc - self.shift_start_time).total_seconds() / 3600
        )

        stats = self.inspection_logger.compute_period_stats(
            self.shift_start_time.isoformat()
        )
        produced = stats["total"]

        self.page.set_shift_progress({
            "produced": produced,
            "target": target,
            "elapsed_hours": elapsed_hours,
            "duration_hours": duration_hours
        })

        if duration_hours <= 0:
            return

        elapsed_fraction = min(elapsed_hours / duration_hours, 1.0)
        expected_by_now = target * elapsed_fraction

        is_behind = produced < expected_by_now * (1 - self.SHIFT_PACE_TOLERANCE)

        if not is_behind:
            return

        if (
            self._last_shift_warning_at is not None
            and (
                time.perf_counter() - self._last_shift_warning_at
                < self.SHIFT_WARNING_COOLDOWN_SECONDS
            )
        ):
            return

        self._last_shift_warning_at = time.perf_counter()

        self._notify_shift_behind_pace(produced, target, expected_by_now)

    def _notify_shift_behind_pace(self, produced, target, expected_by_now):

        settings = self.telegram_settings_manager.load()

        if not settings.is_configured():
            return

        band_name = (
            self.current_band.name
            if self.current_band is not None
            else "?"
        )

        text = (
            f"⏱ Vardiya hedefinin gerisinde - {band_name}\n"
            f"Üretim: {produced} / {target} "
            f"(bu saatte beklenen: ~{int(expected_by_now)})"
        )

        chat_ids = self._telegram_chat_ids(settings.chat_id)

        for chat_id in chat_ids:

            callback = self._telegram_retry_on_failure_callback(
                kind="message",
                bot_token=settings.bot_token,
                chat_id=chat_id,
                text=text
            )

            TelegramNotifier(settings.bot_token, chat_id).send_message_async(
                text, on_sent=callback
            )

    # -------------------------------------------------
    # Kamera Netliği (Bulanıklık) Takibi
    # -------------------------------------------------

    def _maybe_check_blur(self, frame):
        """
        Kameradan gelen görüntünün net olup olmadığını periyodik
        olarak kontrol eder (Laplacian varyansı - bkz. BlurDetector).
        Tek bir kötü kare (ör. kasa hareket ederken oluşan geçici
        bulanıklık) uyarı tetiklemez; BLUR_STREAK_THRESHOLD kadar
        ARDIŞIK kontrolde de bulanık çıkarsa (sürekli bir durum -
        lens kirli, odak kaymış) arayüzde ve Telegram'da bildirilir.
        """

        now = time.perf_counter()

        if (
            now - self._last_blur_check_attempt
            < self.BLUR_CHECK_INTERVAL_SECONDS
        ):
            return

        self._last_blur_check_attempt = now

        if self.current_band is None:
            return

        sharpness = self.blur_detector.compute_sharpness(frame)

        if self.debug_dialog is not None:
            self.debug_dialog.set_current_sharpness(sharpness)

        is_blurry = sharpness < self.current_band.blur_threshold

        if is_blurry:
            self.blur_streak += 1
        else:
            self.blur_streak = 0
            self.page.hide_blur_warning()
            return

        if self.blur_streak < self.BLUR_STREAK_THRESHOLD:
            return

        self.page.show_blur_warning(sharpness)

        if (
            self._last_blur_warning_at is not None
            and (
                time.perf_counter() - self._last_blur_warning_at
                < self.BLUR_WARNING_COOLDOWN_SECONDS
            )
        ):
            return

        self._last_blur_warning_at = time.perf_counter()

        self._notify_blur_detected(sharpness)

    def _notify_blur_detected(self, sharpness):

        settings = self.telegram_settings_manager.load()

        if not settings.is_configured():
            return

        band_name = (
            self.current_band.name
            if self.current_band is not None
            else "?"
        )

        text = (
            f"📷 Kamera görüntüsü bulanık görünüyor - {band_name}\n"
            f"Netlik: {sharpness:.1f} (eşik: "
            f"{self.current_band.blur_threshold:.1f}). Lens kirli/"
            f"buğulu olabilir ya da odak kaymış olabilir."
        )

        chat_ids = self._telegram_chat_ids(settings.chat_id)

        for chat_id in chat_ids:

            callback = self._telegram_retry_on_failure_callback(
                kind="message",
                bot_token=settings.bot_token,
                chat_id=chat_id,
                text=text
            )

            TelegramNotifier(settings.bot_token, chat_id).send_message_async(
                text, on_sent=callback
            )

    # -------------------------------------------------
    # Referans Fotoğrafı Yaşlanma Hatırlatıcısı
    # -------------------------------------------------

    def _maybe_check_reference_age(self):
        """
        Işık/kamera koşulları zamanla kayabileceğinden, referans
        fotoğrafı (dosyanın son değiştirilme tarihinden bu yana)
        band.reference_max_age_days'ten daha eskiyse hatırlatır.
        Birincil kameranın yanı sıra varsa ek kamera kanallarının
        referansları da kontrol edilir.
        """

        now = time.perf_counter()

        if (
            now - self._last_reference_age_check_attempt
            < self.REFERENCE_AGE_CHECK_INTERVAL_SECONDS
        ):
            return

        self._last_reference_age_check_attempt = now

        if self.current_band is None:
            return

        max_age_days = self.current_band.reference_max_age_days

        if max_age_days <= 0:
            self.page.hide_reference_age_warning()
            return

        stale_channels = self._find_stale_reference_channels(max_age_days)

        if not stale_channels:
            self.page.hide_reference_age_warning()
            return

        self.page.show_reference_age_warning(
            f"Referans fotoğrafı eski görünüyor ({max_age_days}+ gün): "
            f"{', '.join(stale_channels)}"
        )

        if (
            self._last_reference_age_warning_at is not None
            and (
                time.perf_counter() - self._last_reference_age_warning_at
                < self.REFERENCE_AGE_WARNING_COOLDOWN_SECONDS
            )
        ):
            return

        self._last_reference_age_warning_at = time.perf_counter()

        self._notify_reference_age(stale_channels, max_age_days)

    def _find_stale_reference_channels(self, max_age_days) -> list:

        stale = []

        if self._is_reference_stale(self.current_band.reference, max_age_days):
            stale.append("Birincil")

        for channel in self.current_band.cameras:

            if self._is_reference_stale(channel.reference, max_age_days):
                stale.append(channel.name)

        return stale

    def _is_reference_stale(self, reference_path, max_age_days) -> bool:

        if not reference_path.exists():
            return False

        age_seconds = time.time() - reference_path.stat().st_mtime

        return age_seconds >= max_age_days * 86400

    def _notify_reference_age(self, stale_channels, max_age_days):

        settings = self.telegram_settings_manager.load()

        if not settings.is_configured():
            return

        band_name = (
            self.current_band.name
            if self.current_band is not None
            else "?"
        )

        text = (
            f"🕒 Referans fotoğrafı eskimiş - {band_name}\n"
            f"{max_age_days}+ gündür yenilenmedi: "
            f"{', '.join(stale_channels)}\n"
            "Işık/kamera koşulları değiştiyse referansı yenilemeyi "
            "düşünün."
        )

        chat_ids = self._telegram_chat_ids(settings.chat_id)

        for chat_id in chat_ids:

            callback = self._telegram_retry_on_failure_callback(
                kind="message",
                bot_token=settings.bot_token,
                chat_id=chat_id,
                text=text
            )

            TelegramNotifier(settings.bot_token, chat_id).send_message_async(
                text, on_sent=callback
            )

    # -------------------------------------------------
    # Otomatik Yedekleme
    # -------------------------------------------------

    def _maybe_run_auto_backup(self):
        """
        Bandın otomatik yedekleme ayarı açıksa ve son yedeklemenin
        üzerinden auto_backup_interval_hours'tan fazla süre geçtiyse,
        arka planda bir yedekleme başlatır (dosya kopyalama işlemi
        UI thread'ini bloklamasın diye). Eski yedekler otomatik
        temizlenir - bkz. BackupManager.backup_and_cleanup.
        """

        now = time.perf_counter()

        if (
            now - self._last_backup_check_attempt
            < self.BACKUP_CHECK_INTERVAL_SECONDS
        ):
            return

        self._last_backup_check_attempt = now

        if self.current_band is None:
            return

        if not self.current_band.auto_backup_enabled:
            return

        destination = self.current_band.auto_backup_destination

        if not destination:
            return

        now_utc = datetime.now(timezone.utc)

        if self.current_band.last_auto_backup_at:

            try:

                last_backup_at = datetime.fromisoformat(
                    self.current_band.last_auto_backup_at
                )

                elapsed_hours = (
                    (now_utc - last_backup_at).total_seconds() / 3600
                )

                if elapsed_hours < self.current_band.auto_backup_interval_hours:
                    return

            except Exception:
                pass

        if (
            self._backup_thread is not None
            and self._backup_thread.is_alive()
        ):
            return

        band = self.current_band
        keep_count = band.auto_backup_keep_count

        def _run():

            try:

                self.backup_manager.backup_and_cleanup(
                    band, destination, keep_count
                )

            except Exception as e:

                app_logger.warning(
                    "Otomatik yedekleme başarısız: %s -> %s (%s)",
                    band.name, destination, e
                )

                return

            updated_band = self.band_manager.load_band(band.id)
            updated_band.last_auto_backup_at = now_utc.isoformat()
            self.band_manager.save_band(updated_band)

            if band is self.current_band:
                self.current_band.last_auto_backup_at = now_utc.isoformat()

            app_logger.info(
                "Otomatik yedekleme tamamlandı: %s -> %s",
                band.name, destination
            )

        self._backup_thread = threading.Thread(target=_run, daemon=True)
        self._backup_thread.start()

    # -------------------------------------------------
    # ArUco Marker ile Otomatik Model Tespiti
    # -------------------------------------------------

    def _handle_marker_model_detection(self, result) -> bool:
        """
        Bu karede görülen sol-üst tanı marker ID'sini işler:
        - Aynı ID MARKER_SWITCH_CONFIRM_FRAMES kadar ardışık
          görülmeden hiçbir şey yapmaz (titreme filtresi).
        - Zaten seçili modelin marker'ıysa dokunmaz.
        - Bilinen bir modelin marker'ıysa o modele otomatik geçer.
        - Hiçbir modelle eşleşmiyorsa "tanınmayan kasa" akışını
          tetikler ve True döner (bu karede OK/NG kararı
          loglanmamalı/Telegram'a bildirilmemeli).
        """

        candidate_id = result.get("identity_marker_id")

        if candidate_id == self._pending_marker_candidate:
            self._pending_marker_streak += 1
        else:
            self._pending_marker_candidate = candidate_id
            self._pending_marker_streak = 1

        if self._pending_marker_streak < self.MARKER_SWITCH_CONFIRM_FRAMES:
            return False

        if candidate_id is None:
            return False

        current_marker_id = (
            self.current_model.marker_id
            if self.current_model is not None
            else None
        )

        if candidate_id == current_marker_id:
            self.page.hide_unknown_kasa_warning()
            return False

        model = self._marker_id_to_model.get(candidate_id)

        if model is not None:
            self._switch_to_model_by_marker(model)
            return False

        self._handle_unknown_kasa(candidate_id, result)
        return True

    def _switch_to_model_by_marker(self, model):

        index = next(
            i for i, m in enumerate(self.models) if m is model
        )

        app_logger.info(
            "[%s] kasa modeli marker ile otomatik değişti: %s -> %s "
            "(marker %s)",
            self.operator_name,
            self.current_model.name if self.current_model else "-",
            model.name,
            model.marker_id
        )

        self.page.model_combo.blockSignals(True)
        self.page.model_combo.setCurrentIndex(index)
        self.page.model_combo.blockSignals(False)

        # recipe_manager + inspection_controller'ı yeniden kurar.
        self._select_model(index)

        self.page.hide_unknown_kasa_warning()

    def _handle_unknown_kasa(self, candidate_id, result):

        self.page.show_unknown_kasa_warning(
            f"Tanınmayan kasa (marker {candidate_id}) — mühendis "
            "incelemesi için kaydedildi."
        )

        if candidate_id == self._last_unknown_marker_id_captured:
            # Aynı bilinmeyen kasa hâlâ kamerada - her karede tekrar
            # fotoğraf/kayıt oluşturma.
            return

        self._last_unknown_marker_id_captured = candidate_id

        roi_states = {
            name: data.get("state")
            for name, data in (result.get("results") or {}).items()
        }

        image = result.get("reference_display")

        if image is None:
            image = result.get("reference")

        self.unknown_kasa_capture_manager.save(
            self.current_band, image, candidate_id, roi_states
        )

        self._notify_unknown_kasa(candidate_id)

    def _notify_unknown_kasa(self, candidate_id):

        if (
            self._last_unknown_kasa_notified_at is not None
            and (
                time.perf_counter() - self._last_unknown_kasa_notified_at
                < self.UNKNOWN_KASA_NOTIFY_COOLDOWN_SECONDS
            )
        ):
            return

        self._last_unknown_kasa_notified_at = time.perf_counter()

        settings = self.telegram_settings_manager.load()

        if not settings.is_configured():
            return

        band_name = (
            self.current_band.name
            if self.current_band is not None
            else "?"
        )

        text = (
            f"❓ Tanınmayan kasa - {band_name}\n"
            f"Marker ID: {candidate_id}. Fotoğraf ve göz durumları "
            "kaydedildi, model tanımı gerekiyor."
        )

        for chat_id in self._telegram_chat_ids(settings.chat_id):

            callback = self._telegram_retry_on_failure_callback(
                kind="message",
                bot_token=settings.bot_token,
                chat_id=chat_id,
                text=text
            )

            TelegramNotifier(settings.bot_token, chat_id).send_message_async(
                text, on_sent=callback
            )

    # -------------------------------------------------
    # Telegram Reaksiyon ile NG -> OK Düzeltme
    # -------------------------------------------------

    def _start_telegram_reaction_poller(self):

        settings = self.telegram_settings_manager.load()

        if not settings.react_to_confirm or not settings.is_configured():
            return

        self.telegram_reaction_poller = TelegramReactionPoller(
            settings.bot_token,
            on_reaction=self._on_telegram_reaction
        )

        self.telegram_reaction_poller.start()

    def _stop_telegram_reaction_poller(self):

        if self.telegram_reaction_poller is not None:

            self.telegram_reaction_poller.stop()
            self.telegram_reaction_poller = None

    def _on_telegram_reaction(self, message_id: int, emoji: str):
        """
        TelegramReactionPoller'ın arka plan thread'inden çağrılır.
        Sadece veri/DB katmanına dokunur (thread-safe), Qt widget'larına
        DOKUNMAZ.
        """

        settings = self.telegram_settings_manager.load()

        if emoji != settings.confirm_emoji:
            return

        if self.inspection_logger is None:
            return

        record_id = self.inspection_logger.find_record_by_telegram_message_id(
            message_id
        )

        if record_id is None:
            return

        self.inspection_logger.mark_reviewed_ok(
            record_id,
            operator_name=f"Telegram ({emoji})"
        )

        app_logger.info(
            "[Telegram] #%s kaydı %s tepkisiyle OK'e çevrildi",
            record_id,
            emoji
        )

    def _connect_arduino(self):

        if self.arduino_controller is not None:
            self.arduino_controller.close()
            self.arduino_controller = None

        port = self.current_band.arduino_port

        if not port:
            return

        self.arduino_controller = ArduinoController(port)

        if self.arduino_controller.is_connected():

            app_logger.info(
                "Arduino'ya bağlandı: %s (band=%s)",
                port,
                self.current_band.name
            )

        else:

            app_logger.warning(
                "Arduino'ya bağlanılamadı: %s (band=%s)",
                port,
                self.current_band.name
            )

    def _attempt_arduino_reconnect(self):
        """
        Kamera gibi Arduino da (kablo çekilmesi, USB kopması vb.)
        bağlantı koptuğunda kendiliğinden tekrar bağlanmayı dener.
        Her tick'te değil, ARDUINO_RECONNECT_INTERVAL_SECONDS'ta bir
        denenir (bağlantı denemesi ~2 saniye bloklayabildiği için).
        """

        now = time.perf_counter()

        if (
            now - self.last_arduino_reconnect_attempt
            < self.ARDUINO_RECONNECT_INTERVAL_SECONDS
        ):
            return

        self.last_arduino_reconnect_attempt = now

        port = self.arduino_controller.port

        self.arduino_controller.close()
        self.arduino_controller = ArduinoController(port)

        if self.arduino_controller.is_connected():

            app_logger.info(
                "Arduino ile bağlantı yeniden kuruldu: %s",
                port
            )

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

        now = time.perf_counter()

        if now - self.last_reconnect_attempt < self.RECONNECT_INTERVAL_SECONDS:
            return

        self.last_reconnect_attempt = now

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

        self.page.set_status("Kamera yeniden bağlandı - CONNECTED")

    # -------------------------------------------------
    # Disk Alanı Kontrolü
    # -------------------------------------------------

    def _check_disk_space(self):

        now = time.perf_counter()

        if now - self.last_disk_check < self.DISK_CHECK_INTERVAL_SECONDS:
            return

        self.last_disk_check = now

        check_path = (
            self.current_band.root
            if self.current_band is not None
            else self.band_manager.root
        )

        free_gb = get_free_space_gb(check_path)

        if free_gb < self.DISK_WARNING_THRESHOLD_GB:

            self.page.show_disk_warning(free_gb)

            if not self.disk_warning_active:

                app_logger.warning(
                    "Disk alanı azalıyor: %.1f GB kaldı (band=%s)",
                    free_gb,
                    self.current_band.name if self.current_band is not None else "?"
                )

                self.disk_warning_active = True

        else:

            self.page.hide_disk_warning()
            self.disk_warning_active = False

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
            self.page.set_debug_button_text("&Debug Göster")

    # -------------------------------------------------
    # Reference Kaydet
    # -------------------------------------------------

    def _on_save_reference_clicked(self):

        if self.current_band is None or self.last_reference is None:

            QMessageBox.warning(
                self.window,
                "Uyarı",
                "Kaydedilecek bir reference görüntüsü yok."
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
            "Reference güncellendi."
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
            self.page.set_debug_button_text("&Debug Gizle")

            return

        if self.debug_dialog.isVisible():
            self.debug_dialog.hide()
            self.debug_enabled = False
            self.page.set_debug_button_text("&Debug Göster")
        else:
            self.debug_dialog.show()
            self.debug_enabled = True
            self.page.set_debug_button_text("&Debug Gizle")

    def _on_debug_dialog_closed(self):

        self.debug_enabled = False
        self.page.set_debug_button_text("&Debug Göster")

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
            "Bu bandın tüm inspection geçmişi ve NG fotoğrafları "
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
            self.page.set_status("CONNECTED")
        else:
            self.page.set_status("Kamera bekleniyor / Parça yok")

        if self.debug_enabled and self.debug_dialog is not None:

            self.debug_dialog.show_debug(result["debug"])
