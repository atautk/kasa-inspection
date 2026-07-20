import cv2

DICTS = {
    "4X4_50": cv2.aruco.DICT_4X4_50,
    "4X4_100": cv2.aruco.DICT_4X4_100,
    "5X5_50": cv2.aruco.DICT_5X5_50,
    "6X6_250": cv2.aruco.DICT_6X6_250,
    "ARUCO_ORIGINAL": cv2.aruco.DICT_ARUCO_ORIGINAL,
}

cap = cv2.VideoCapture(0)

while True:

    ret, frame = cap.read()

    if not ret:
        break

    for name, dictionary in DICTS.items():

        detector = cv2.aruco.ArucoDetector(
            cv2.aruco.getPredefinedDictionary(dictionary),
            cv2.aruco.DetectorParameters()
        )

        corners, ids, _ = detector.detectMarkers(frame)

        if ids is not None:
            print(f"{name} -> {ids.flatten()}")

    cv2.imshow("Test", frame)

    if cv2.waitKey(1) == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()