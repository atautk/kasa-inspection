import cv2
import numpy as np


class ReferenceFrame:

    def __init__(self, width=1200, height=800):

        self.width = width
        self.height = height
        self.last_frame = None

    def generate(self, image, frame_corners):

        # Köşe konumu yoksa (kasa/markerlar tamamen kaybolduysa) eski,
        # artık anlamsız hale gelmiş görüntüyü döndürmek yerine hafızayı
        # temizleyip net bir şekilde "referans yok" bildir.
        if frame_corners is None or len(frame_corners) != 4:

            self.last_frame = None

            return None

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