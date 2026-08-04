import time
import winsound

import cv2

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox

from modules.core.aruco_detector import ArucoDetector
from modules.core.localization import LocalizationEngine
from modules.core.reference_frame import ReferenceFrame
from modules.core.inspection_engine import InspectionEngine
from modules.core.decision_engine import DecisionEngine
from modules.core.arduino_controller import ArduinoController

from modules.configuration.band_manager import BandManager
from modules.configuration.model_manager import ModelManager
from modules.configuration.reference_manager import ReferenceManager
from modules.configuration.model_recipe_adapter import ModelRecipeAdapter
from modules.configuration.inspection_logger import InspectionLogger
from modules.configuration.ng_capture_manager import NGCaptureManager

from modules.ui.roi_manager import ROIManager
from modules.ui.inspection.debug_dialog import DebugDialog
from modules.ui.inspection.log_viewer_dialog import LogViewerDialog

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

        self.bands = []
        self.models = []

        self.current_band = None
        self.current_model = None

        self.recipe_manager = ModelRecipeAdapter(None)

        self.roi_manager = ROIManager()

        self.inspection_controller = None
        self.inspection_logger = None
        self.ng_capture_manager = NGCaptureManager()
        self.arduino_controller = None
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
    # Band / Model Yükleme
    # -------------------------------------------------

    def _load_bands(self):

        self.bands = self.band_manager.list_bands()

        self.page.set_band_list(
            [band.name for band in self.bands]
        )

        if self.bands:
            self._select_band(0)
        else:
            self.page.set_status("Hiç band bulunamadı")

    def _select_band(self, index):

        if index < 0 or index >= len(self.bands):
            return

        self.current_band = self.bands[index]

        self.inspection_logger = InspectionLogger(self.current_band)

        if self.debug_dialog is not None:
            self.debug_dialog.set_threshold(self.current_band.threshold)

        self.roi_manager.load(self.current_band.roi)

        self.reference_image = self.reference_manager.load(
            self.current_band
        )

        self.models = self.model_manager.list_models(
            self.current_band
        )

        self.page.set_model_list(
            [model.name for model in self.models]
        )

        if self.models:
            self._select_model(0)
        else:
            self.current_model = None
            self.recipe_manager = ModelRecipeAdapter(None)
            self._build_inspection_controller()

    def _select_model(self, index):

        if index < 0 or index >= len(self.models):
            return

        self.current_model = self.models[index]

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

    def _build_inspection_controller(self):

        decision_engine = DecisionEngine()

        if self.current_band is not None:
            decision_engine.set_threshold(self.current_band.threshold)

        self.inspection_controller = InspectionController(
            ArucoDetector(),
            LocalizationEngine(),
            ReferenceFrame(width=1200, height=800),
            InspectionEngine(),
            self.roi_manager,
            self.recipe_manager,
            decision_engine
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

        self._build_inspection_controller()

        self._connect_arduino()

        self.running = True
        self.camera_connected = True
        self.camera_failure_count = 0

        self.page.set_start_button_text("Durdur")
        self.page.enable_selection(False)
        self.page.set_status("CONNECTED")

        self.last_tick_time = time.perf_counter()

        self.timer.start()

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

    def _open_camera(self, camera_index):

        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.CAMERA_HEIGHT)

        if not cap.isOpened():
            cap.release()
            return None

        return cap

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

        if self.cap is not None:
            self.cap.release()
            self.cap = None

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

        self.page.set_start_button_text("Başlat")
        self.page.enable_selection(True)
        self.page.set_status("Durduruldu")
        self.page.clear_image()
        self.page.clear_results()
        self.page.hide_ng_alert()
        self.last_alert_state = None

        if self.debug_dialog is not None:
            self.debug_dialog.hide()
            self.debug_enabled = False
            self.page.set_debug_button_text("Debug Göster")

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

            self.debug_dialog.threshold_spinbox.valueChanged.connect(
                self._on_threshold_changed
            )

            self.debug_dialog.finished.connect(self._on_debug_dialog_closed)

            self.debug_dialog.show()

            self.debug_enabled = True
            self.page.set_debug_button_text("Debug Gizle")

            return

        if self.debug_dialog.isVisible():
            self.debug_dialog.hide()
            self.debug_enabled = False
            self.page.set_debug_button_text("Debug Göster")
        else:
            self.debug_dialog.show()
            self.debug_enabled = True
            self.page.set_debug_button_text("Debug Gizle")

    def _on_debug_dialog_closed(self):

        self.debug_enabled = False
        self.page.set_debug_button_text("Debug Göster")

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
    # Kamera Döngüsü
    # -------------------------------------------------

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

        display = result["reference_display"]

        if display is None:
            display = frame

        self.page.set_image(display)

        self.page.set_results(result["results"])

        overall_result = None

        if result["results"]:

            overall_result = (
                "OK"
                if all(data["ok"] for data in result["results"].values())
                else "NG"
            )

        self._update_ng_alert(overall_result)

        if self.arduino_controller is not None:

            if result["results"]:
                self.arduino_controller.send_results(result["results"])
            else:
                self.arduino_controller.send_waiting()

        if (
            self.inspection_logger is not None
            and result["results"]
            and self.inspection_logger.should_log(result["results"])
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

            self.inspection_logger.log(
                result["results"],
                model_name,
                image_path
            )

        localization = result["localization"]

        if localization is not None:

            self.page.set_mode(localization["mode"])
            self.page.set_confidence(localization["confidence"])

        self.page.set_performance(fps, inspection_time)

        if result["results"]:
            self.page.set_status("CONNECTED")
        else:
            self.page.set_status("Kamera bekleniyor / Parça yok")

        if self.debug_enabled and self.debug_dialog is not None:

            self.debug_dialog.show_debug(result["debug"])
