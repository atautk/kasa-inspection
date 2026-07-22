import cv2
import numpy as np


class ReferenceFrame:

    def __init__(self, width=1200, height=800):

        self.width = width
        self.height = height
        self.last_frame = None

    def generate(self, image, frame_corners):

        # 4 köşe gelmediyse son başarılı görüntüyü döndür
        if frame_corners is None:
            return self.last_frame

        if len(frame_corners) != 4:
            return self.last_frame

        src = np.array(frame_corners, dtype=np.float32)

        dst = np.array([
            [0, 0],
            [self.width, 0],
            [0, self.height],
            [self.width, self.height]
        ], dtype=np.float32)

        matrix = cv2.getPerspectiveTransform(src, dst)

        reference = cv2.warpPerspective(
            image,
            matrix,
            (self.width, self.height)
        )

        self.last_frame = reference

        return reference