import json
from pathlib import Path

from PySide6.QtWidgets import (
    QInputDialog,
    QMessageBox,
    QListWidgetItem,
    QFileDialog,
    QLineEdit
)
from PySide6.QtCore import Qt, QTimer

from modules.configuration.band_manager import BandManager
from modules.configuration.reference_manager import ReferenceManager
from modules.configuration.model_manager import ModelManager
from modules.configuration.configuration_validator import ConfigurationValidator
from modules.configuration.band_export_manager import BandExportManager
from modules.utils.logger import get_logger

# modules/ui/configurator/configurator_controller.py -> proje kökü
ROOT = Path(__file__).resolve().parents[3]

from modules.core.camera import Camera
from modules.core.aruco_detector import ArucoDetector
from modules.core.localization import LocalizationEngine
from modules.core.reference_frame import ReferenceFrame
from modules.core.frame_processor import FrameProcessor

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

        band_page.validate_button.clicked.connect(
            self.validate_band
        )

        band_page.save_threshold_button.clicked.connect(
            self.save_threshold
        )

        band_page.export_button.clicked.connect(
            self.export_band
        )

        band_page.import_button.clicked.connect(
            self.import_band
        )

        band_page.add_operator_button.clicked.connect(
            self.add_operator
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

        roi_page = self.window.roi_page

        roi_page.save_button.clicked.connect(
            self.save_rois
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

        page.set_threshold(self.current_band.threshold)
        page.set_arduino_port(self.current_band.arduino_port)
        page.enable_threshold_controls(True)

        self.load_reference_tab()

        QMessageBox.information(

            self.window,

            "Başarılı",

            f"{self.current_band.name} açıldı."

        )

    # -------------------------------------------------

    def save_threshold(self):

        if self.current_band is None:
            return

        page = self.window.band_page

        self.current_band.threshold = page.get_threshold()
        self.current_band.arduino_port = page.get_arduino_port()

        self.band_manager.save_band(self.current_band)

        app_logger.info(
            "[%s] band ayarları değiştirildi: %s -> eşik %%%.1f, "
            "arduino portu '%s'",
            self.operator_name,
            self.current_band.name,
            self.current_band.threshold,
            self.current_band.arduino_port
        )

        QMessageBox.information(

            self.window,

            "Başarılı",

            f"Eşik değeri %{self.current_band.threshold:.1f} olarak "
            f"kaydedildi."

        )

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

    def add_operator(self):

        if self.operator_manager is None:
            return

        name, ok = QInputDialog.getText(
            self.window,
            "Yeni Operatör",
            "Operatör Adı"
        )

        if not ok:
            return

        name = name.strip()

        if name == "":
            return

        pin, ok = QInputDialog.getText(
            self.window,
            "Yeni Operatör",
            f"{name} için PIN belirleyin",
            QLineEdit.Password
        )

        if not ok or pin == "":
            return

        try:

            self.operator_manager.create_operator(name, pin)

        except ValueError as e:

            QMessageBox.warning(
                self.window,
                "Hata",
                str(e)
            )

            return

        app_logger.info(
            "[%s] yeni operatör eklendi: %s",
            self.operator_name,
            name
        )

        QMessageBox.information(
            self.window,
            "Başarılı",
            f"{name} operatör olarak eklendi."
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
    # ROI Sekmesi
    # -------------------------------------------------

    def load_roi_tab(self):

        if self.current_band is None:
            return

        page = self.window.roi_page

        if not self.reference_manager.exists(self.current_band):

            page.clear()
            page.set_status(
                "Reference bulunamadı. Önce Reference sekmesinden "
                "fotoğraf çekin."
            )
            return

        image = self.reference_manager.load(self.current_band)
        page.set_background(image)

        rois = self._read_roi_file()
        page.load_rois(rois)

        page.set_status(
            f"{len(rois)} ROI yüklendi."
        )

    # -------------------------------------------------

    def save_rois(self):

        if self.current_band is None:
            return

        rois = self.window.roi_page.get_rois()

        data = {
            "version": "1.0",
            "rois": rois
        }

        with open(
            self.current_band.roi,
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

        app_logger.info(
            "[%s] ROI'ler kaydedildi: %s (%d ROI)",
            self.operator_name,
            self.current_band.name,
            len(rois)
        )

        QMessageBox.information(

            self.window,

            "Başarılı",

            f"{len(rois)} ROI roi.json dosyasına kaydedildi."

        )

    # -------------------------------------------------

    def _read_roi_file(self) -> list:

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

        self.current_model = None

        page.set_status(f"{len(models)} model bulundu.")

    # -------------------------------------------------

    def on_model_selected(self, current, previous):

        page = self.window.model_page

        model_id = page.get_selected_model_id()

        if model_id is None:

            self.current_model = None
            page.clear_roi_checklist()
            return

        self.current_model = self.model_manager.load_model(
            self.current_band,
            model_id
        )

        roi_names = self._roi_names()

        page.set_roi_checklist(
            roi_names,
            self.current_model.expected_rois
        )

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

        self.model_manager.save_model(
            self.current_band,
            self.current_model
        )

        app_logger.info(
            "[%s] model kaydedildi: %s / %s -> beklenen ROI'ler: %s",
            self.operator_name,
            self.current_band.name,
            self.current_model.name,
            self.current_model.expected_rois
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

        return [
            roi.get("name", "")
            for roi in self._read_roi_file()
        ]

    # -------------------------------------------------
    # Yardımcılar
    # -------------------------------------------------

    def _update_roi_tab_state(self):

        has_reference = self.reference_manager.exists(
            self.current_band
        )

        self.window.tabs.setTabEnabled(2, has_reference)