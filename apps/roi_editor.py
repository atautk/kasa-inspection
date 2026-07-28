import cv2

from modules.core.aruco_detector import ArucoDetector
from modules.core.localization import LocalizationEngine
from modules.core.reference_frame import ReferenceFrame
from modules.core.inspection_engine import InspectionEngine

from modules.ui.roi_manager import ROIManager

BOX_NAME = "kasa_001"

ROI_FILE = f"recipes/{BOX_NAME}/roi.json"

REFERENCE_FILE = f"recipes/{BOX_NAME}/reference.png"

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

aruco = ArucoDetector()

localizer = LocalizationEngine()

reference_frame = ReferenceFrame(
    width=1200,
    height=800
)

inspection = InspectionEngine()

roi_manager = ROIManager()

roi_manager.load(ROI_FILE)

cv2.namedWindow(
    "ROI EDITOR",
    cv2.WINDOW_NORMAL
)

cv2.resizeWindow(
    "ROI EDITOR",
    1400,
    900
)

cv2.setMouseCallback(
    "ROI EDITOR",
    roi_manager.mouse_callback
)

print("----------------------------------")
print("ROI EDITOR")
print("----------------------------------")
print("LMB : Add Point")
print("RMB : Finish Polygon")
print("Drag : Move ROI")
print("D : Delete")
print("S : Save ROI")
print("R : Save Reference")
print("ESC : Exit")
print("----------------------------------")

while True:

    ret, frame = cap.read()

    if not ret:
        break

    # -----------------------------
    # ArUco Algılama
    # -----------------------------

    markers = aruco.detect(frame)

    for marker in markers.values():

        cv2.polylines(
            frame,
            [marker.corners.astype(int)],
            True,
            (0,255,0),
            2
        )

    # -----------------------------
    # Localization
    # -----------------------------

    localization = localizer.update(markers)

    # -----------------------------
    # Perspective
    # -----------------------------

    reference = reference_frame.generate(
        frame,
        localization["frame_corners"]
    )

    if reference is not None:

        display = roi_manager.draw(reference)

        display = roi_manager.draw_info(display)

        cv2.imshow(
            "ROI EDITOR",
            display
        )

    else:
        temp = frame.copy

        cv2.putText(
            temp,
            "Waiting for 4 markers...",
            (20,40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0,0,255),
            2
        )

        cv2.imshow(
            "ROI EDITOR",
            temp
        )

    key = cv2.waitKey(1) & 0xFF

    roi_manager.key_handler(key)

    if key == ord("s"):

        roi_manager.save(ROI_FILE)

    elif key == ord("r"):

        if reference is not None:

            inspection.save_reference(
                reference,
                REFERENCE_FILE
            )

    elif key == 27:

        break
    roi_manager.key_handler(key)


cap.release()

cv2.destroyAllWindows()

