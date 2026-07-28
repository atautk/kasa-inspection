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
from modules.core.recipe_manager import RecipeManager
from modules.core.decision_engine import DecisionEngine

from modules.ui.roi_manager import ROIManager
from modules.ui.dashboard import Dashboard
from modules.ui.debug_view import DebugView

from modules.controllers.inspection_controller import InspectionController
from modules.controllers.keyboard_controller import KeyboardController


# -------------------------------------------------
# DOSYALAR
# -------------------------------------------------

BOX_NAME = "kasa_001"

ROI_FILE = ROOT / "recipes" / BOX_NAME / "roi.json"

REFERENCE_FILE = ROOT / "recipes" / BOX_NAME / "reference.png"

RECIPE_FILE = ROOT / "recipes" / BOX_NAME / "recipes.json"


# -------------------------------------------------
# KAMERA
# -------------------------------------------------

cap = cv2.VideoCapture(
    0,
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
    ROI_FILE
)

recipe_manager = RecipeManager()
recipe_manager.load(
    RECIPE_FILE
)

decision_engine = DecisionEngine()


reference_image = inspection_engine.load_reference(
    REFERENCE_FILE
)


inspection_controller = InspectionController(

    aruco,

    localizer,

    reference_frame,

    inspection_engine,

    roi_manager,

    recipe_manager,

    decision_engine

)


dashboard = Dashboard()

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

logs = []


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
    # Dashboard
    # -----------------------------------------

    logs.clear()

    for name, data in result["results"].items():

        if data["ok"]:

            logs.append(f"{name}: OK")

        else:

            logs.append(f"{name}: NG")

    dashboard.show(

        result,

        recipe_manager.recipe["recipe_name"],

        fps,

        inspection_time,

        logs

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

            ROI_FILE

        )

    # Reference Kaydet

    elif action == KeyboardController.ACTION_SAVE_REFERENCE:

        if result["reference"] is not None:

            inspection_engine.save_reference(

                result["reference"],

                REFERENCE_FILE

            )

            reference_image = inspection_engine.load_reference(

                REFERENCE_FILE

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

dashboard.close()

debug_view.close()

cv2.destroyAllWindows()