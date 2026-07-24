import cv2
import numpy as np


class ArucoDetector:

    def __init__(self):

        dictionary = cv2.aruco.getPredefinedDictionary(
            cv2.aruco.DICT_ARUCO_ORIGINAL
        )

        parameters = cv2.aruco.DetectorParameters()

        self.detector = cv2.aruco.ArucoDetector(
            dictionary,
            parameters
        )

    def detect(self, frame):

        corners, ids, _ = self.detector.detectMarkers(frame)

        if ids is None:
            return {}

        markers = {}

        for marker_corner, marker_id in zip(corners, ids.flatten()):

            pts = marker_corner.reshape(4, 2)

            center = np.mean(pts, axis=0)

            markers[int(marker_id)] = {
                "corners": pts,
                "center": center
            }

        return markers