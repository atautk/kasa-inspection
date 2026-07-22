import cv2
from modules.aruco_detector import ArucoDetector
from modules.reference_frame import ReferenceFrame
from modules.localization import LocalizationEngine


# -----------------------------
# Kamera Ayarları
# -----------------------------
CAMERA_INDEX = 0      # Eğer çalışmazsa 1 veya 2 dene.

cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("❌ Kamera açılamadı!")
    exit()

# İsteğe bağlı çözünürlük
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

aruco = ArucoDetector()
reference_frame = ReferenceFrame()
localizer = LocalizationEngine()

print("=" * 40)
print(" KASA INSPECTION ")
print("=" * 40)
print("Q veya ESC ile çıkabilirsiniz.")
print()

# -----------------------------
# Ana Döngü
# -----------------------------
while True:

    ret, frame = cap.read()

    if not ret:
        print("❌ Kameradan görüntü alınamadı.")
        break

    corners, ids = aruco.detect(frame)

    if ids is not None:

        cv2.aruco.drawDetectedMarkers(
            frame,
            corners,
            ids
        )

        id_text = "ID: " + " ".join(map(str, ids.flatten()))
        
        markers = {}
        for marker_corner, marker_id in zip(corners, ids.flatten()):
            markers[int(maker_id)]={
                "corners":marker_corner,
                "center":marker_corner.reshape(4, 2).mean(axis=0)
            }
        
        localization = localizer.update(markers)

        print(
    f"Mode: {localization['mode']} | "
    f"Visible: {localization['visible']} | "
    f"Confidence: {localization['confidence']}%"
)
        
        print(localization["mode"])
        
        reference=reference_frame.generate(frame, localization["frame_corners"])

        if reference is not None:
            cv2.imshow("Reference Frame", reference)
        
        for marker_id in sorted(markers.keys()):

            center = markers[marker_id]["center"]

            print(f"ID {marker_id} -> {center}")
    else:

        id_text = "ID: Yok"

    # Bilgi Yazıları
    cv2.putText(
        frame,
        id_text,
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2
    )

    cv2.putText(
        frame,
        "Q : Cikis",
        (20, 70),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 0, 0),
        2
    )

    cv2.imshow("KASA INSPECTION", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q") or key == 27:
        break

# -----------------------------
# Temizlik
# -----------------------------
cap.release()
cv2.destroyAllWindows() 
