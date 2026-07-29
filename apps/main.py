import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


import cv2
import time

from modules.core.aruco_detector import ArucoDetector
from modules.core.localization import LocalizationEngine
from modules.core.reference_frame import ReferenceFrame
from modules.core.inspection_engine import InspectionEngine
from modules.core.decision_engine import DecisionEngine

from modules.configuration.band_manager import BandManager
from modules.configuration.reference_manager import ReferenceManager
from modules.configuration.model_manager import ModelManager
from modules.configuration.model_recipe_adapter import ModelRecipeAdapter

from modules.ui.roi_manager import ROIManager
from modules.ui.debug_view import DebugView

from modules.controllers.inspection_controller import InspectionController
from modules.controllers.keyboard_controller import KeyboardController


# -------------------------------------------------
# BAND SEÇ
# -------------------------------------------------

band_manager = BandManager(root=ROOT / "configuration")

bands = band_manager.list_bands()

if not bands:

    print("Hiç bant bulunamadı.")

    print("Önce Configurator ile bant oluştur.")

    exit()

band = bands[0]

print(f"[INFO] Band: {band.name}")


# -------------------------------------------------
# MODEL SEÇ
# -------------------------------------------------

model_manager = ModelManager()

models = model_manager.list_models(band)

if not models:

    print(f"[UYARI] '{band.name}' bandında hiç model yok.")

    print("Configurator > Models sekmesinden en az bir model oluştur.")

    selected_model = None

else:

    selected_model = models[0]

    print(f"[INFO] Model: {selected_model.name}")


# -------------------------------------------------
# KAMERA
# -------------------------------------------------

cap = cv2.VideoCapture(
    band.camera,
    cv2.CAP_DSHOW
)

cap.set(
    cv2.CAP_PROP_FRAME_WIDTH,
    1280
)

cap.set(
    cv2.CAP_PROP_FRAME_HEIGHT,
    720
)

if not cap.isOpened():

    print("Kamera açılamadı.")

    exit()


# -------------------------------------------------
# MODÜLLER
# -------------------------------------------------

aruco = ArucoDetector()

localizer = LocalizationEngine()

reference_frame = ReferenceFrame(
    width=1200,
    height=800
)

inspection_engine = InspectionEngine()

roi_manager = ROIManager()
roi_manager.load(
    band.roi
)

recipe_manager = ModelRecipeAdapter(selected_model)

decision_engine = DecisionEngine()

reference_manager = ReferenceManager()

reference_image = reference_manager.load(band)

if reference_image is None:

    print(f"[UYARI] '{band.name}' bandında reference.png yok.")

    print("Configurator > Reference sekmesinden fotoğraf çek.")


inspection_controller = InspectionController(

    aruco,

    localizer,

    reference_frame,

    inspection_engine,

    roi_manager,

    recipe_manager,

    decision_engine

)


debug_view = DebugView()

keyboard = KeyboardController()


# -------------------------------------------------
# PENCERE
# -------------------------------------------------

cv2.namedWindow(
    "REFERENCE FRAME",
    cv2.WINDOW_NORMAL
)

cv2.resizeWindow(
    "REFERENCE FRAME",
    1200,
    800
)

cv2.setMouseCallback(
    "REFERENCE FRAME",
    roi_manager.mouse_callback
)


# -------------------------------------------------
# DEĞİŞKENLER
# -------------------------------------------------

fps = 0

inspection_time = 0


print("-------------------------------------")
print("KASA INSPECTION")
print("-------------------------------------")
print("S : ROI Kaydet")
print("R : Reference Kaydet")
print("P : Print")
print("D : Debug")
print("Q : Çıkış")
print("-------------------------------------")


# -------------------------------------------------
# ANA DÖNGÜ
# -------------------------------------------------

running = True

while running:

    start = time.perf_counter()

    ret, frame = cap.read()

    if not ret:

        break

    result = inspection_controller.process(

        frame,

        reference_image

    )

    # -----------------------------------------
    # Hata Kontrolü
    # -----------------------------------------

    if not result["success"]:

        print(result["error"])

        continue

    # -----------------------------------------
    # Reference Frame
    # -----------------------------------------

    if result["reference_display"] is not None:

        cv2.imshow(

            "REFERENCE FRAME",

            result["reference_display"]

        )

    # -----------------------------------------
    # Debug
    # -----------------------------------------

    debug_view.show(

        result["debug"]

    )

    # -----------------------------------------
    # Keyboard
    # -----------------------------------------

    action = keyboard.update()

    # ROI Kaydet

    if action == KeyboardController.ACTION_SAVE_ROI:

        roi_manager.save(

            band.roi

        )

    # Reference Kaydet

    elif action == KeyboardController.ACTION_SAVE_REFERENCE:

        if result["reference"] is not None:

           reference_manager.save(

               band,

               result["reference"]
           )

           reference_image = reference_manager.load(
               band
           )

           print("[INFO] Reference güncellendi.")

    # Sonuçları Yazdır

    elif action == KeyboardController.ACTION_PRINT:

        print()

        print("------------------------------")

        for name, data in result["results"].items():

            print(

                f"{name:>3} | "

                f"{data['state']:>5} | "

                f"{data['expected']:>5} | "

                f"{'OK' if data['ok'] else 'NG'} | "

                f"{data['change_ratio']:.2f}%"

            )

        print("------------------------------")

    # Debug Aç / Kapat

    elif action == KeyboardController.ACTION_TOGGLE_DEBUG:

        debug_view.toggle()

    # Çıkış

    elif action == KeyboardController.ACTION_EXIT:

        running = False

    # -----------------------------------------
    # FPS
    # -----------------------------------------

    end = time.perf_counter()

    inspection_time = (end - start) * 1000

    fps = 1 / (end - start + 1e-6)


# -------------------------------------------------
# KAPAT
# -------------------------------------------------

cap.release()

debug_view.close()

cv2.destroyAllWindows()