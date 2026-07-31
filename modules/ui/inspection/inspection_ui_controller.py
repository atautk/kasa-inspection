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

from modules.configuration.band_manager import BandManager
from modules.configuration.model_manager import ModelManager
from modules.configuration.reference_manager import ReferenceManager
from modules.configuration.model_recipe_adapter import ModelRecipeAdapter
from modules.configuration.inspection_logger import InspectionLogger
from modules.configuration.ng_capture_manager import NGCaptureManager

from modules.ui.roi_manager import ROIManager
from modules.ui.debug_view import DebugView
from modules.ui.inspection.log_viewer_dialog import LogViewerDialog

from modules.controllers.inspection_controller import InspectionController
from modules.utils.logger import get_logger

app_logger = get_logger()


class InspectionUIController:

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

        self.bands = []
        self.models = []

        self.current_band = None
        self.current_model = None

        self.recipe_manager = ModelRecipeAdapter(None)

        self.roi_manager = ROIManager()

        self.inspection_controller = None
        self.inspection_logger = None
        self.ng_capture_manager = NGCaptureManager()
        self.last_alert_state = None

        self.reference_image = None
        self.last_reference = None

        self.cap = None
        self.running = False

        self.camera_connected = True
        self.camera_failure_count = 0
        self.last_reconnect_attempt = 0.0

        self.debug_enabled = False
        self.debug_view = DebugView()
        self.debug_view.disable()

        self.last_tick_time = None

        self.log_dialog = None

        self.timer = QTimer()
        self.timer.setInterval(self.TIMER_INTERVAL_MS)
        self.timer.timeout.connect(self._tick)

        self._connect_signals()

        self._load_bands()

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

        self.running = True
        self.camera_connected = True
        self.camera_failure_count = 0

        self.page.set_start_button_text("Durdur")
        self.page.enable_selection(False)
        self.page.set_status("CONNECTED")

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

    def _stop(self):

        self.timer.stop()

        if self.cap is not None:
            self.cap.release()
            self.cap = None

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

        self.debug_view.close()

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

        self.debug_enabled = not self.debug_enabled

        if self.debug_enabled:
            self.debug_view.enable()
            self.page.set_debug_button_text("Debug Gizle")
        else:
            self.debug_view.disable()
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
            operator_name=self.operator_name
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

        self.page.set_status("CONNECTED")

        if self.debug_enabled:

            self.debug_view.show(result["debug"])

            cv2.waitKey(1)
