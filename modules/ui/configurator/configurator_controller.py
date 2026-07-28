from PySide6.QtWidgets import (
    QInputDialog,
    QMessageBox,
    QListWidgetItem
)
from PySide6.QtCore import Qt, QTimer

from modules.configuration.band_manager import BandManager
from modules.configuration.reference_manager import ReferenceManager

from modules.core.camera import Camera
from modules.core.aruco_detector import ArucoDetector
from modules.core.localization import LocalizationEngine
from modules.core.reference_frame import ReferenceFrame
from modules.core.frame_processor import FrameProcessor


class ConfiguratorController:

    def __init__(self, window):

        self.window = window

        self.band_manager = BandManager()
        self.reference_manager = ReferenceManager()

        self.current_band = None

        # ---------- Reference Capture ----------

        self.camera = None

        self.aruco = ArucoDetector()
        self.localizer = LocalizationEngine()
        self.reference_frame = ReferenceFrame()

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

        self.load_reference_tab()

        QMessageBox.information(

            self.window,

            "Başarılı",

            f"{self.current_band.name} açıldı."

        )

    # -------------------------------------------------
    # Reference Sekmesi
    # -------------------------------------------------

    def load_reference_tab(self):

        self.stop_camera()

        page = self.window.reference_page

        self.last_reference_frame = None

        if self.reference_manager.exists(self.current_band):

            image = self.reference_manager.load(self.current_band)

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

        self.camera = Camera(
            camera_index=self.current_band.camera
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

        self.reference_manager.save(

            self.current_band,

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

        self.reference_manager.delete(self.current_band)

        self.last_reference_frame = None

        page = self.window.reference_page

        page.clear_preview()
        page.set_status("Reference silindi. Kamerayı açın.")
        page.enable_retake_button(False)
        page.enable_capture(False)

        self._update_roi_tab_state()

        self.start_camera()

    # -------------------------------------------------
    # Yardımcılar
    # -------------------------------------------------

    def _update_roi_tab_state(self):

        has_reference = self.reference_manager.exists(
            self.current_band
        )

        self.window.tabs.setTabEnabled(2, has_reference)