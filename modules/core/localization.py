import numpy as np


class LocalizationEngine:

    REQUIRED_MARKERS = [0, 1, 2, 3]

    def __init__(self):

        self.last_frame_corners = None

    # -------------------------------------------------

    def update(self, markers):

        visible = sum(
            marker in markers
            for marker in self.REQUIRED_MARKERS
        )

        mode = self._get_mode(visible)

        frame_corners = self._build_frame(markers)

        if frame_corners is not None:
            self.last_frame_corners = frame_corners.copy()
        else:
            frame_corners = self.last_frame_corners

        return {

            "mode": mode,

            "visible": visible,

            "confidence": self.get_confidence(visible),

            "frame_corners": frame_corners

        }

    # -------------------------------------------------

    def _build_frame(self, markers):

        # ---------- NORMAL ----------

        if all(marker in markers for marker in self.REQUIRED_MARKERS):

            return np.float32([

                markers[0].corners[0],

                markers[1].corners[1],

                markers[2].corners[3],

                markers[3].corners[2]

            ])

        # ---------- RECOVERY ----------

        if self.last_frame_corners is None:
            return None

        corners = self.last_frame_corners.copy()

        if 0 in markers:
            corners[0] = markers[0].corners[0]

        if 1 in markers:
            corners[1] = markers[1].corners[1]

        if 2 in markers:
            corners[2] = markers[2].corners[3]

        if 3 in markers:
            corners[3] = markers[3].corners[2]

        return corners

    # -------------------------------------------------

    def _get_mode(self, visible):

        if visible == 4:
            return "NORMAL"

        if visible == 3:
            return "RECOVERY"

        if visible == 2:
            return "ESTIMATE"

        return "FAIL"

    # -------------------------------------------------

    def get_confidence(self, visible):

        table = {

            4: 100,

            3: 90,

            2: 70,

            1: 20,

            0: 0

        }

        return table.get(visible, 0)