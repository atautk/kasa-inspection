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

        try:

            results = {}

            difference = None

            debug = None

            for roi in self.roi_manager.get_rois():

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
                    continue

                # ---------------------------------
                # Compare
                # ---------------------------------

                compare = self.inspection.compare(
                    reference_crop,
                    current_crop
                )

                state = self.decision.detect(
                    compare
                )

                expected = self.recipe.expected(
                    roi["name"]
                )

                results[roi["name"]] = {

                    "state": state,

                    "expected": expected,

                    "ok": state == expected,

                    "change_ratio": compare["change_ratio"],

                    "changed_pixels": compare["changed_pixels"]

                }

                difference = compare["difference"]

                debug = compare

            return {

                "success": True,

                "error": None,

                "results": results,

                "difference": difference,

                "debug": debug

            }

        except Exception as e:

            return {

                "success": False,

                "error": str(e),

                "results": {},

                "difference": None,

                "debug": None

            }