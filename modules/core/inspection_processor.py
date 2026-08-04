import traceback


class InspectionProcessor:

    def __init__(
        self,
        inspection_engine,
        roi_manager,
        recipe_manager,
        decision_engine
    ):

        self.inspection = inspection_engine
        self.roi_manager = roi_manager
        self.recipe = recipe_manager
        self.decision = decision_engine

    # -------------------------------------------------
    # Inspection
    # -------------------------------------------------

    def process(
        self,
        reference,
        reference_image
    ):

        results = {}

        difference = {}

        debug = {}

        try:

            for roi in self.roi_manager.get_rois():

                try:

                    roi_name = roi["name"]
                    points = roi["points"]

                    # ---------------------------------
                    # Crop
                    # ---------------------------------

                    reference_crop = self.inspection.crop_polygon(
                        reference_image,
                        points
                    )

                    current_crop = self.inspection.crop_polygon(
                        reference,
                        points
                    )

                    if (
                        reference_crop.size == 0
                        or
                        current_crop.size == 0
                    ):

                        results[roi_name] = {

                            "state": "INVALID",

                            "expected": self.recipe.expected(
                                roi_name
                            ),

                            "ok": False,

                            "change_ratio": 0,

                            "changed_pixels": 0

                        }

                        continue

                    # ---------------------------------
                    # Compare
                    # ---------------------------------

                    compare = self.inspection.compare(
                        reference_crop,
                        current_crop
                    )

                    roi_threshold = self.recipe.threshold_for(roi_name)

                    state = self.decision.detect(
                        compare,
                        threshold=roi_threshold
                    )

                    expected = self.recipe.expected(
                        roi_name
                    )

                    results[roi_name] = {

                        "state": state,

                        "expected": expected,

                        "ok": state == expected,

                        "change_ratio": compare["change_ratio"],

                        "changed_pixels": compare["changed_pixels"]

                    }

                    difference[roi_name] = compare.get(
                        "difference"
                    )

                    debug[roi_name] = compare

                except Exception as e:

                    traceback.print_exc()

                    results[roi["name"]] = {

                        "state": "ERROR",

                        "expected": None,

                        "ok": False,

                        "change_ratio": 0,

                        "changed_pixels": 0,

                        "error": str(e)

                    }

            return {

                "success": True,

                "error": None,

                "results": results,

                "difference": difference,

                "debug": debug

            }

        except Exception as e:

            traceback.print_exc()

            return {

                "success": False,

                "error": str(e),

                "results": {},

                "difference": {},

                "debug": {}

            }