import cv2

from modules.aruco_detector import ArucoDetector
from modules.localization import LocalizationEngine
from modules.reference_frame import ReferenceFrame
from modules.roi_manager import ROIManager
from modules.inspection_engine import InspectionEngine
from modules.recipe_manager import RecipeManager
from modules.decision_engine import DecisionEngine


# ---------------------------------
# Dosyalar
# ---------------------------------

ROI_FILE = "recipes/kasa_001/roi.json"
REFERENCE_FILE = "recipes/kasa_001/reference.png"
RECIPE_FILE = "recipes/kasa_001/recipes.json"

# ---------------------------------
# Kamera
# ---------------------------------

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

if not cap.isOpened():
    print("Kamera açılamadı.")
    exit()

# ---------------------------------
# Modüller
# ---------------------------------

aruco = ArucoDetector()

localizer = LocalizationEngine()

reference_frame = ReferenceFrame(
    width=1200,
    height=800
)

roi_manager = ROIManager()
roi_manager.load(ROI_FILE)

inspection = InspectionEngine()

recipe = RecipeManager()
recipe.load(RECIPE_FILE)

decision = DecisionEngine()

reference_image = inspection.load_reference(
    REFERENCE_FILE
)

# ---------------------------------
# Pencereler
# ---------------------------------

cv2.namedWindow("REFERENCE FRAME")

cv2.setMouseCallback(
    "REFERENCE FRAME",
    roi_manager.mouse_callback
)

print("KASA INSPECTION")
print("R : Reference Kaydet")
print("S : ROI Kaydet")
print("Q : Çıkış")

# ---------------------------------
# Ana Döngü
# ---------------------------------

while True:

    ret, frame = cap.read()

    if not ret:
        break

    markers = aruco.detect(frame)

    for marker in markers.values():

        cv2.polylines(

            frame,

            [marker["corners"].astype(int)],

            True,

            (0,255,0),

            2

        )

    localization = localizer.update(markers)

    reference = reference_frame.generate(

        frame,

        localization["frame_corners"]

    )

    cv2.putText(

        frame,

        f"MODE : {localization['mode']}",

        (20,35),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.8,

        (0,255,0),

        2

    )

    cv2.imshow(
        "KASA INSPECTION",
        frame
    )

    if reference is not None:

        display = roi_manager.draw(reference)

        cv2.imshow(
            "REFERENCE FRAME",
            display
        )

    # ---------------------------------
    # ROI Analizi
    # ---------------------------------

    if (
        reference is not None
        and reference_image is not None
        and roi_manager.selected_roi is not None
    ):

        points = roi_manager.selected_roi["points"]

        reference_crop = inspection.crop_polygon(
            reference_image,
            points
        )

        current_crop = inspection.crop_polygon(
            reference,
            points
        )

        if (
            reference_crop.size != 0
            and current_crop.size != 0
        ):

            result = inspection.compare(
                reference_crop,
                current_crop
            )

            cv2.imshow(
                "Reference Crop",
                result["reference"]
            )

            cv2.imshow(
                "Current Crop",
                result["current"]
            )

            state = decision.detect(result)

            expected = recipe.expected(
                roi_manager.selected_roi["name"]
            )

            cv2.putText(
                result["current"],
                f"STATE : {state}",
                (10,25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0,0,255),
                2
            )

            cv2.putText(
                result["current"],
                f"EXPECTED : {expected}",
                (10,50),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255,0,0),
                2
            )

            cv2.putText(
                result["current"],
                f"PIXELS : {result['changed_pixels']}",
                (10,75),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0,255,0),
                2
            )

            cv2.putText(
                result["current"],
                f"DIFF : %{result['change_ratio']:.2f}",
                (10,100),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0,255,0),
                2
            )

            cv2.imshow(
                roi_manager.selected_roi["name"],
                result["current"]
            )

            cv2.imshow(
                "Difference",
                result["difference"]
            )

            cv2.imshow(
                "Binary",
                result["binary"]
            )

    # ---------------------------------
    # Tuşlar
    # ---------------------------------

    key = cv2.waitKey(1) & 0xFF

    roi_manager.key_handler(key)

    if key == ord("s"):

        roi_manager.save(
            ROI_FILE
        )

    elif key == ord("r"):

        if reference is not None:

            inspection.save_reference(
                reference,
                REFERENCE_FILE
            )

            reference_image = inspection.load_reference(
                REFERENCE_FILE
            )

            print("[INFO] Reference kaydedildi.")

    elif key == ord("q") or key == 27:

        break

cap.release()

cv2.destroyAllWindows()