import cv2

from modules.aruco_detector import ArucoDetector
from modules.localization import LocalizationEngine
from modules.reference_frame import ReferenceFrame
from modules.roi_manager import ROIManager
from modules.inspection_engine import InspectionEngine
from modules.recipe_manager import RecipeManager


REFERENCE_FILE = "recipes/kasa_001/reference.png"

# ---------------------------------
# Kamera
# ---------------------------------

CAMERA_INDEX = 0

cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("Kamera açılamadı.")
    exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)


# ---------------------------------
# Modüller
# ---------------------------------

aruco = ArucoDetector()

localizer = LocalizationEngine()

inspection = InspectionEngine()

reference_frame = ReferenceFrame(
    width=1200,
    height=800
)

roi_manager = ROIManager()

ROI_FILE = "recipes/kasa_001/roi.json"
roi_manager.load(ROI_FILE)

recipe = RecipeManager()

recipe.load("recipes/kasa_001/recipes.json")



print("KASA INSPECTION")
print("Q : Çıkış")


cv2.namedWindow("REFERENCE FRAME")

cv2.setMouseCallback(
    "REFERENCE FRAME",
    roi_manager.mouse_callback
)


# ---------------------------------
# Ana Döngü
# ---------------------------------

while True:

    ret, frame = cap.read()

    if not ret:
        break

    # -----------------------------
    # ArUco
    # -----------------------------

    markers = aruco.detect(frame)

    # Markerları çiz

    for marker in markers.values():

        cv2.polylines(
            frame,
            [marker["corners"].astype(int)],
            True,
            (0, 255, 0),
            2
        )

    # -----------------------------
    # Localization
    # -----------------------------

    localization = localizer.update(markers)

    # -----------------------------
    # Reference Frame
    # -----------------------------

    reference = reference_frame.generate(
        frame,
        localization["frame_corners"]
    )

    # -----------------------------
    # Bilgiler
    # -----------------------------

    cv2.putText(
        frame,
        f"MODE : {localization['mode']}",
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2
    )

    cv2.putText(
        frame,
        f"VISIBLE : {localization['visible']}",
        (20, 70),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 0),
        2
    )

    cv2.putText(
        frame,
        f"CONFIDENCE : {localization['confidence']}%",
        (20, 105),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 200, 255),
        2
    )

    cv2.imshow("KASA INSPECTION", frame)

    if reference is not None:
        reference_display = roi_manager.draw(reference)
        cv2.imshow("REFERENCE FRAME", reference_display)
    
    if (roi_manager.selected_roi is not None):
        crop = inspection.crop_polygon(
            reference,
            roi_manager.selected_roi["points"]
        )
        if crop.size != 0:
            
            result = inspection.analyze(crop)

            print(
                roi_manager.selected_roi["name"],
                recipe.expected(
                    roi_manager.selected_roi["name"]
                )
            )
            
            cv2.putText(
                crop,
                f"Mean: {result['mean']}",
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )
            cv2.putText(
                crop,
                f"Std: {result['std']}",
                (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )
            cv2.putText(
                crop,
                f"Edges: {result['edge_count']}",
                (10, 75),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )
            cv2.imshow(
                roi_manager.selected_roi["name"],
                crop
            )

    key = cv2.waitKey(1) & 0xFF
    
    roi_manager.key_handler(key)

    if key == ord("s"):
        roi_manager.save(ROI_FILE)
    

    if key == ord("q") or key == 27:
        break
    
    if key == ord("r"):
        if reference is not None:
            inspection.save_reference(
                reference,
                REFERENCE_FILE
            )
            reference_image = inspection.load_reference(
                REFERENCE_FILE  
            )


cv2.putText(
    crop,
    f"Mean : {result['mean']}",
    (10,25),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.55,
    (0,255,0),
    2
)

cv2.putText(
    crop,
    f"Std : {result['std']}",
    (10,50),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.55,
    (0,255,0),
    2
)

cv2.putText(
    crop,
    f"Edges : {result['edge_count']}",
    (10,75),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.55,
    (0,255,0),
    2
)

cv2.putText(
    crop,
    f"White : %{result['white_ratio']}",
    (10,100),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.55,
    (0,255,0),
    2
)

print(
    roi_manager.selected_roi["name"],
    result
)

cap.release()
cv2.destroyAllWindows()