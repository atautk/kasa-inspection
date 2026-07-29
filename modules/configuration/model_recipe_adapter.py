class ModelRecipeAdapter:
    """
    Eski RecipeManager arayüzünü (expected / recipe_name / is_loaded)
    yeni Model (expected_rois) yapısına uyarlar.

    InspectionProcessor bunu RecipeManager yerine kullanır, böylece
    Core tarafında (InspectionProcessor, DecisionEngine) hiçbir
    değişiklik yapmaya gerek kalmaz.

    Kural: model.expected_rois listesinde olan her ROI "FULL",
    listede olmayan her ROI "EMPTY" kabul edilir.
    """

    def __init__(self, model):

        self.model = model

    # -------------------------------------------------

    def expected(self, roi_name: str) -> str:

        if self.model is None:
            return "EMPTY"

        if roi_name in self.model.expected_rois:
            return "FULL"

        return "EMPTY"

    # -------------------------------------------------

    def is_loaded(self) -> bool:

        return self.model is not None

    # -------------------------------------------------

    def recipe_name(self) -> str:

        if self.model is None:
            return ""

        return self.model.name