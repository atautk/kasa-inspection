import cv2
import time
from modules.core.aruco_detector import ArucoDetector
from modules.core.localization import LocalizationEngine
from modules.core.reference_frame import ReferenceFrame
from modules.ui.roi_manager import ROIManager
from modules.core.inspection_engine import InspectionEngine
from modules.core.recipe_manager import RecipeManager
from modules.core.decision_engine import DecisionEngine
from modules.ui.dashboard import Dashboard


# -------------------------------------------------
# Dosyalar
# -------------------------------------------------

ROI_FILE = "recipes/kasa_001/roi.json"
REFERENCE_FILE = "recipes/kasa_001/reference.png"
RECIPE_FILE = "recipes/kasa_001/recipes.json"

# -------------------------------------------------
# Kamera
# -------------------------------------------------

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

if not cap.isOpened():
    print("Kamera açılamadı.")
    exit()

# -------------------------------------------------
# Modüller
# -------------------------------------------------

aruco = ArucoDetector()

localizer = LocalizationEngine()

reference_frame = ReferenceFrame(
    width=1200,
    height=800
)

inspection = InspectionEngine()

roi_manager = ROIManager()
roi_manager.load(ROI_FILE)

recipe = RecipeManager()
recipe.load(RECIPE_FILE)

decision = DecisionEngine()

reference_image = inspection.load_reference(
    REFERENCE_FILE
)

dashboard = Dashboard()

logs = []

fps = 0

inspection_time = 0

# -------------------------------------------------
# Pencere
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
cv2.namedWindow(
    "Dashboard",
    cv2.WINDOW_NORMAL
)

cv2.resizeWindow(
    "Dashboard",
    1600,
    900
)

cv2.setMouseCallback(
    "REFERENCE FRAME",
    roi_manager.mouse_callback
)

print("-------------------------------------")
print("KASA INSPECTION")
print("-------------------------------------")
print("S : ROI Kaydet")
print("R : Reference Kaydet")
print("Q : Çıkış")
print("-------------------------------------")

# -------------------------------------------------
# Ana Döngü
# -------------------------------------------------

while True:
    
    start_time = time.perf_counter()

    ret, frame = cap.read()

    if not ret:
        break

    # -----------------------------------------
    # ArUco
    # -----------------------------------------

    markers = aruco.detect(frame)

    for marker in markers.values():

        cv2.polylines(

            frame,

            [marker["corners"].astype(int)],

            True,

            (0,255,0),

            2

        )

    # -----------------------------------------
    # Localization
    # -----------------------------------------

    localization = localizer.update(markers)

    # -----------------------------------------
    # Perspective
    # -----------------------------------------

    reference = reference_frame.generate(

        frame,

        localization["frame_corners"]

    )

    # -----------------------------------------
    # Bilgiler
    # -----------------------------------------

    cv2.putText(

        frame,

        f"MODE : {localization['mode']}",

        (20,35),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.7,

        (0,255,0),

        2

    )

    cv2.putText(

        frame,

        f"VISIBLE : {localization['visible']}",

        (20,65),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.7,

        (255,255,0),

        2

    )

    cv2.putText(

        frame,

        f"CONFIDENCE : {localization['confidence']}%",

        (20,95),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.7,

        (0,200,255),

        2

    )

    cv2.imshow(
        "KASA INSPECTION",
        frame
    )

    # -----------------------------------------
    # Reference hazır mı?
    # -----------------------------------------

    if (
        reference is not None
        and reference_image is not None
    ):

        results = {}

        # Devamı 2. parçada...
                # -----------------------------------------
        # Tüm ROI'leri Analiz Et
        # -----------------------------------------

        for roi in roi_manager.get_rois():

            points = roi["points"]

            reference_crop = inspection.crop_polygon(
                reference_image,
                points
            )

            current_crop = inspection.crop_polygon(
                reference,
                points
            )

            if (
                reference_crop.size == 0
                or
                current_crop.size == 0
            ):
                continue

            result = inspection.compare(
                reference_crop,
                current_crop
            )
            
            difference = result["difference"]

            state = decision.detect(result)

            expected = recipe.expected(
                roi["name"]
            )

            ok = (state == expected)

            results[roi["name"]] = {

                "state": state,

                "expected": expected,

                "ok": ok,

                "change_ratio": result["change_ratio"],

                "changed_pixels": result["changed_pixels"]

            }

        # -----------------------------------------
        # Sonuçları Çiz
        # -----------------------------------------

        logs.clear()

        for name,data in results.items():
            if data["ok"]:
                logs.append(f"{name}:OK")
            else:
                logs.append(f"{name}:NG")
        
        display = roi_manager.draw_results(
            reference,
            results
        )

        dashboard_image = dashboard.render(
            frame,

            display,

            difference,

            results,

            recipe.recipe["recipe_name"],

            "INSPECTION",

            fps,

            inspection_time,

            logs
        )
        

        cv2.imshow(
            "Dashboard",
            dashboard_image
        )

        # -----------------------------------------
        # Debug (İlk ROI)
        # -----------------------------------------

        if len(results) > 0:

            first_roi = roi_manager.get_rois()[0]

            ref_crop = inspection.crop_polygon(
                reference_image,
                first_roi["points"]
            )

            cur_crop = inspection.crop_polygon(
                reference,
                first_roi["points"]
            )

            debug = inspection.compare(
                ref_crop,
                cur_crop
            )

            cv2.imshow(
                "Reference Crop",
                debug["reference"]
            )

            cv2.imshow(
                "Current Crop",
                debug["current"]
            )

            cv2.imshow(
                "Difference",
                debug["difference"]
            )

            cv2.imshow(
                "Binary",
                debug["binary"]
            )
                # -------------------------------------------------
    # Klavye
    # -------------------------------------------------

    key = cv2.waitKey(1) & 0xFF
    
    if cv2.getWindowProperty(
        "Dashboard",
        cv2.WND_PROP_VISIBLE
    ) < 1:
        break

    roi_manager.key_handler(key)

    # ROI Kaydet
    if key == ord("s"):

        roi_manager.save(
            ROI_FILE
        )

    # Referans Kaydet
    elif key == ord("r"):

        if reference is not None:

            inspection.save_reference(
                reference,
                REFERENCE_FILE
            )

            reference_image = inspection.load_reference(
                REFERENCE_FILE
            )

            print("[INFO] Reference güncellendi.")

    # Sonuçları Yazdır
    elif key == ord("p"):

        print("\n-----------------------------")

        for name, data in results.items():

            print(

                f"{name:>3} | "

                f"{data['state']:>5} | "

                f"{data['expected']:>5} | "

                f"{'OK' if data['ok'] else 'NG'} | "

                f"Diff: %{data['change_ratio']:.2f}"

            )

        print("-----------------------------")
    
    # Çıkış
    elif key == ord("q") or key == 27:

        break
    
    
    end_time = time.perf_counter()

    inspection_time = (end_time - start_time)*100
    
    fps = 1 / (end_time - start_time + 1e-6)


# -------------------------------------------------
# Kapat
# -------------------------------------------------

cap.release()

cv2.destroyAllWindows()
