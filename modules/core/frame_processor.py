class FrameProcessor:

    def __init__(
        self,
        aruco,
        localizer,
        reference_frame
    ):
        self.aruco = aruco
        self.localizer = localizer
        self.reference_frame = reference_frame

    # -------------------------------------------------
    # Frame İşleme
    # -------------------------------------------------

    def process(self, frame):

        try:

            # -----------------------------
            # ArUco Detection
            # -----------------------------

            markers = self.aruco.detect(frame)

            # -----------------------------
            # Localization
            # -----------------------------

            localization = self.localizer.update(
                markers
            )

            # -----------------------------
            # Perspective Transform
            # -----------------------------

            reference = self.reference_frame.generate(
                frame,
                localization["frame_corners"]
            )

            return {

                "success": True,

                "error": None,

                "frame": frame,

                "markers": markers,

                "localization": localization,

                "reference": reference

            }

        except Exception as e:

            return {

                "success": False,

                "error": str(e),

                "frame": frame,

                "markers": {},

                "localization": None,

                "reference": None

            }