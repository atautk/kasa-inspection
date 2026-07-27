import cv2


class DebugView:

    def __init__(self):

        self.enabled = True

        self.windows = [

            "Reference Crop",

            "Current Crop",

            "Difference",

            "Binary"

        ]

    # -------------------------------------------------
    # Debug Pencerelerini Göster
    # -------------------------------------------------

    def show(self, debug):

        if not self.enabled:
            return

        if debug is None:
            return

        images = {

            "Reference Crop": debug["reference"],

            "Current Crop": debug["current"],

            "Difference": debug["difference"],

            "Binary": debug["binary"]

        }

        for window, image in images.items():

            if image is not None:

                cv2.imshow(
                    window,
                    image
                )

    # -------------------------------------------------
    # Debug Pencerelerini Kapat
    # -------------------------------------------------

    def close(self):

        for window in self.windows:

            try:

                cv2.destroyWindow(window)

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