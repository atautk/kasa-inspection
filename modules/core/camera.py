import cv2


class Camera:

    def __init__(
        self,
        camera_index=0,
        width=1920,
        height=1080
    ):

        self.camera_index = camera_index

        self.width = width
        self.height = height

        self.cap = None

    # -------------------------------------------------
    # Kamerayı Aç
    # -------------------------------------------------

    def open(self):

        if self.cap is not None:

            return True

        self.cap = cv2.VideoCapture(
            self.camera_index
        )

        if not self.cap.isOpened():

            self.cap = None
            return False

        self.cap.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            self.width
        )

        self.cap.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            self.height
        )

        return True

    # -------------------------------------------------
    # Frame Oku
    # -------------------------------------------------

    def read(self):

        if self.cap is None:

            return None

        ok, frame = self.cap.read()

        if not ok:

            return None

        return frame

    # -------------------------------------------------
    # Kamera Açık mı?
    # -------------------------------------------------

    def is_open(self):

        return (

            self.cap is not None

            and

            self.cap.isOpened()

        )

    # -------------------------------------------------
    # Kamerayı Kapat
    # -------------------------------------------------

    def release(self):

        if self.cap is not None:

            self.cap.release()

            self.cap = None

    # -------------------------------------------------
    # Destructor
    # -------------------------------------------------

    def __del__(self):

        self.release()