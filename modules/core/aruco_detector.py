import cv2
import numpy as np

from .marker import Marker


class ArucoDetector:

    VALID_MARKERS = {0, 1, 2, 3}

    def __init__(self):

        dictionary = cv2.aruco.getPredefinedDictionary(
            cv2.aruco.DICT_ARUCO_ORIGINAL
        )

        parameters = cv2.aruco.DetectorParameters()

        # Köşe hassasiyetini artır
        parameters.cornerRefinementMethod = (
            cv2.aruco.CORNER_REFINE_SUBPIX
        )

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

            marker_id = int(marker_id)

            if marker_id not in self.VALID_MARKERS:
                continue

            pts = marker_corner.reshape(4, 2)

            center = np.mean(pts, axis=0)

            area = cv2.contourArea(
                pts.astype(np.float32)
            )

            top = pts[1] - pts[0]

            rotation = np.degrees(
                np.arctan2(
                    top[1],
                    top[0]
                )
            )

            markers[marker_id] = Marker(

                id=marker_id,

                corners=pts,

                center=center,

                area=area,

                rotation=rotation

            )

        return markers