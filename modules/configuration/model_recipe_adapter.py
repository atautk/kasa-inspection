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

    def threshold_for(self, roi_name: str):
        """
        Bu model, roi_name için özel bir değişim eşiği tanımlamışsa
        onu döndürür; tanımlamamışsa None döner (bandın genel eşiği
        kullanılır).
        """

        if self.model is None:
            return None

        return self.model.roi_thresholds.get(roi_name)

    # -------------------------------------------------

    def is_loaded(self) -> bool:

        return self.model is not None

    # -------------------------------------------------

    def recipe_name(self) -> str:

        if self.model is None:
            return ""

        return self.model.name


class PrefixedRecipeAdapter:
    """
    Bir kasayı ek bir kamera açısından izlerken kullanılan sarmalayıcı.

    O kanalın ROI editöründe basit isimler (G01, G02...) kullanılır -
    her kanal kendi roi.json'unu bağımsız çizer. Ama Model'in
    expected_rois/roi_thresholds listesinde, birden fazla kanalın
    aynı isimde ROI'si olabileceğinden (ör. iki kanalda da "G01")
    kanal adıyla NİTELENMİŞ isimler saklanır ("Yan:G01" gibi).

    Bu sınıf, kanalın kendi InspectionProcessor'ının basit isimlerle
    çağırdığı expected()/threshold_for() sorgularını, altındaki
    ModelRecipeAdapter'a nitelenmiş isimle iletir - InspectionProcessor
    ve DecisionEngine'de hiçbir değişiklik gerekmez.
    """

    def __init__(self, base_adapter: ModelRecipeAdapter, channel_name: str):

        self.base_adapter = base_adapter
        self.channel_name = channel_name

    # -------------------------------------------------

    def _qualify(self, roi_name: str) -> str:

        return f"{self.channel_name}:{roi_name}"

    # -------------------------------------------------

    def expected(self, roi_name: str) -> str:

        return self.base_adapter.expected(self._qualify(roi_name))

    def threshold_for(self, roi_name: str):

        return self.base_adapter.threshold_for(self._qualify(roi_name))

    def is_loaded(self) -> bool:

        return self.base_adapter.is_loaded()

    def recipe_name(self) -> str:

        return self.base_adapter.recipe_name()