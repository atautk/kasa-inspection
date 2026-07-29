import cv2
import numpy as np


class DebugView:

    WINDOW_NAME = "Debug"

    THUMB_WIDTH = 220
    THUMB_HEIGHT = 160

    TITLE_HEIGHT = 20

    LABELS = [
        ("reference", "Reference"),
        ("current", "Current"),
        ("difference", "Difference"),
        ("binary", "Binary")
    ]

    def __init__(self):

        self.enabled = True

    # -------------------------------------------------
    # Debug Penceresini Göster
    # -------------------------------------------------

    def show(self, debug):

        if not self.enabled:
            return

        if not debug:
            return

        rois = sorted(debug.keys())

        canvas = np.zeros(
            (
                self.THUMB_HEIGHT * len(rois),
                self.THUMB_WIDTH * len(self.LABELS),
                3
            ),
            dtype=np.uint8
        )

        for row, roi_name in enumerate(rois):

            compare = debug[roi_name]

            for col, (key, label) in enumerate(self.LABELS):

                thumb = self._build_thumbnail(
                    compare.get(key),
                    f"{roi_name} - {label}"
                )

                y = row * self.THUMB_HEIGHT
                x = col * self.THUMB_WIDTH

                canvas[
                    y:y + self.THUMB_HEIGHT,
                    x:x + self.THUMB_WIDTH
                ] = thumb

        cv2.imshow(self.WINDOW_NAME, canvas)

    # -------------------------------------------------
    # Küçük Resim Oluştur
    # -------------------------------------------------

    def _build_thumbnail(self, image, title):

        thumb = np.zeros(
            (self.THUMB_HEIGHT, self.THUMB_WIDTH, 3),
            dtype=np.uint8
        )

        if image is not None:

            if len(image.shape) == 2:
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

            resized = cv2.resize(
                image,
                (self.THUMB_WIDTH, self.THUMB_HEIGHT - self.TITLE_HEIGHT)
            )

            thumb[self.TITLE_HEIGHT:, :] = resized

        cv2.rectangle(
            thumb,
            (0, 0),
            (self.THUMB_WIDTH, self.TITLE_HEIGHT),
            (40, 40, 40),
            -1
        )

        cv2.putText(
            thumb,
            title,
            (4, self.TITLE_HEIGHT - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (255, 255, 255),
            1
        )

        cv2.rectangle(
            thumb,
            (0, 0),
            (self.THUMB_WIDTH - 1, self.THUMB_HEIGHT - 1),
            (90, 90, 90),
            1
        )

        return thumb

    # -------------------------------------------------
    # Debug Penceresini Kapat
    # -------------------------------------------------

    def close(self):

        try:

            cv2.destroyWindow(self.WINDOW_NAME)

        except cv2.error:

            pass

    # -------------------------------------------------
    # Enable
    # -------------------------------------------------

    def enable(self):

        self.enabled = True

    # -------------------------------------------------
    # Disable
    # -------------------------------------------------

    def disable(self):

        self.enabled = False

        self.close()

    # -------------------------------------------------
    # Toggle
    # -------------------------------------------------

    def toggle(self):

        if self.enabled:

            self.disable()

        else:

            self.enable()

    # -------------------------------------------------
    # Durum
    # -------------------------------------------------

    def is_enabled(self):

        return self.enabled
