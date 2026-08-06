import cv2


from modules.core.frame_processor import FrameProcessor
from modules.core.inspection_processor import InspectionProcessor


class InspectionController:

    def __init__(
        self,
        aruco,
        localizer,
        reference_frame,
        inspection_engine,
        roi_manager,
        recipe_manager,
        decision_engine
    ):

        self.frame_processor = FrameProcessor(
            aruco,
            localizer,
            reference_frame
        )

        self.inspection_processor = InspectionProcessor(
            inspection_engine,
            roi_manager,
            recipe_manager,
            decision_engine
        )

        self.roi_manager = roi_manager

    # -------------------------------------------------
    # Inspection
    # -------------------------------------------------

    def process(
        self,
        frame,
        reference_image
    ):

        frame_data = self.frame_processor.process(
            frame
        )

        if not frame_data["success"]:

            return {

                "success": False,

                "error": frame_data["error"],

                "frame": frame,

                "reference": None,

                "reference_display": None,

                "markers": {},

                "identity_marker_id": None,

                "localization": None,

                "results": {},

                "difference": None,

                "debug": None

            }

        frame = frame_data["frame"]

        reference = frame_data["reference"]

        markers = frame_data["markers"]

        identity_marker_id = frame_data["identity_marker_id"]

        localization = frame_data["localization"]

        # -----------------------------------------
        # Referans Yok
        # -----------------------------------------

        if reference is None:

            return {

                "success": True,

                "error": None,

                "frame": frame,

                "reference": None,

                "reference_display": None,

                "markers": markers,

                "identity_marker_id": identity_marker_id,

                "localization": localization,

                "results": {},

                "difference": None,

                "debug": None

            }

        # -----------------------------------------
        # Reference Image Yok
        # -----------------------------------------

        if reference_image is None:

            return {

                "success": True,

                "error": None,

                "frame": frame,

                "reference": reference,

                "reference_display": reference,

                "markers": markers,

                "identity_marker_id": identity_marker_id,

                "localization": localization,

                "results": {},

                "difference": None,

                "debug": None

            }

        # -----------------------------------------
        # Inspection
        # -----------------------------------------

        inspection = self.inspection_processor.process(

            reference,

            reference_image

        )

        if not inspection["success"]:

            return {

                "success": False,

                "error": inspection["error"],

                "frame": frame,

                "reference": reference,

                "reference_display": reference,

                "markers": markers,

                "identity_marker_id": identity_marker_id,

                "localization": localization,

                "results": {},

                "difference": None,

                "debug": None

            }

        reference_display = self.roi_manager.draw_results(

            reference.copy(),

            inspection["results"]

        )

        return {

            "success": True,

            "error": None,

            "frame": frame,

            "reference": reference,

            "reference_display": reference_display,

            "markers": markers,

            "identity_marker_id": identity_marker_id,

            "localization": localization,

            "results": inspection["results"],

            "difference": inspection["difference"],

            "debug": inspection["debug"]

        }