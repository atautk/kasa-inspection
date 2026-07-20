import numpy as np


class LocalizationEngine:

    def __init__(self):

        self.last_markers = None

    def update(self, markers):

        self.last_markers = markers

        visible = len(markers)

        if visible == 4:
            mode = "NORMAL"

        elif visible == 3:
            mode = "RECOVERY"

        elif visible == 2:
            mode = "ESTIMATE"

        else:
            mode = "FAIL"

        return {
            "mode": mode,
            "visible": visible,
            "markers": markers,
            "points": self.get_points(markers),
            "confidence": self.get_confidence(visible)
        }
    def get_points(self, markers):

        points = []

        for marker_id in [0, 1, 2, 3]:

            if marker_id in markers:
                points.append(markers[marker_id]["center"])
            else:
                points.append(None)

        return points
    def get_confidence(self, visible):

        if visible == 4:
            return 100

        if visible == 3:
            return 90

        if visible == 2:
            return 70

        return 0