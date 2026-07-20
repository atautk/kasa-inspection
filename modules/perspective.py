import cv2
import numpy as np


class PerspectiveTransformer:

    def __init__(self, width=1200, height=800):

        self.width = width
        self.height = height
        self.last_warp = None

    def get_marker_center(self, corners):

        pts = corners.reshape(4, 2)

        return np.mean(pts, axis=0)

    def sort_markers(self, corners, ids):

        markers = {}

        for marker_corner, marker_id in zip(corners, ids.flatten()):

            markers[int(marker_id)] = {
                "corner": marker_corner,
                "center": self.get_marker_center(marker_corner)
            }

        return markers

    def warp(self, image, points):

        if any(p is None for p in points):
            return self.last_warp

        src = np.float32(points)

        dst = np.float32([
            [0, 0],
            [self.width, 0],
            [0, self.height],
            [self.width, self.height]
        ])

        matrix = cv2.getPerspectiveTransform(src, dst)

        warped = cv2.warpPerspective(
            image,
            matrix,
            (self.width, self.height)
        )

        self.last_warp = warped

        return warped