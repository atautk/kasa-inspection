import traceback


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

        if frame is None:

            return {

                "success": False,

                "error": "Frame is None",

                "frame": None,

                "markers": {},

                "localization": None,

                "reference": None

            }

        try:

            markers = self.aruco.detect(frame)

            localization = self.localizer.update(
                markers
            )

            reference = None

            if localization["frame_corners"] is not None:

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

            traceback.print_exc()

            return {

                "success": False,

                "error": str(e),

                "frame": frame,

                "markers": {},

                "localization": None,

                "reference": None

            }