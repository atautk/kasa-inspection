import numpy as np


class LocalizationEngine:

    def __init__(self):

        self.last_frame_corners = None

    def update(self, markers):

        visible = len(markers)

        if visible == 4:
            mode = "NORMAL"

        elif visible == 3:
            mode = "RECOVERY"

        elif visible == 2:
            mode = "ESTIMATE"

        else:
            mode = "FAIL"

        frame_corners = self.get_frame_corners(markers)

        if frame_corners is not None:
            self.last_frame_corners = frame_corners
        else:
            frame_corners = self.last_frame_corners

        return {
            "mode": mode,
            "visible": visible,
            "confidence": self.get_confidence(visible),
            "frame_corners": frame_corners
        }

    def get_frame_corners(self, markers):

        required = [0, 1, 2, 3]

        for marker_id in required:
            if marker_id not in markers:
                return None

        return np.float32([
            markers[0]["center"],
            markers[1]["center"],
            markers[2]["center"],
            markers[3]["center"]
        ])

    def get_confidence(self, visible):

        if visible == 4:
            return 100

        elif visible == 3:
            return 90

        elif visible == 2:
            return 70

        return 0