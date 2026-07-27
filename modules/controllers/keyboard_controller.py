import cv2


class KeyboardController:

    ACTION_NONE = "NONE"
    ACTION_SAVE_ROI = "SAVE_ROI"
    ACTION_SAVE_REFERENCE = "SAVE_REFERENCE"
    ACTION_PRINT = "PRINT"
    ACTION_TOGGLE_DEBUG = "TOGGLE_DEBUG"
    ACTION_EXIT = "EXIT"

    def __init__(self):
        pass

    # -------------------------------------------------
    # Klavye Güncelle
    # -------------------------------------------------

    def update(self):

        key = cv2.waitKey(1) & 0xFF

        if key == ord("s"):
            return self.ACTION_SAVE_ROI

        elif key == ord("r"):
            return self.ACTION_SAVE_REFERENCE

        elif key == ord("p"):
            return self.ACTION_PRINT

        elif key == ord("d"):
            return self.ACTION_TOGGLE_DEBUG

        elif key == ord("q") or key == 27:
            return self.ACTION_EXIT

        return self.ACTION_NONE