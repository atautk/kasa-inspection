import json
from pathlib import Path


class RecipeManager:

    def __init__(self):

        self.recipe = {}

        self.filename = None

    # -------------------------------------------------
    # Recipe Yükle
    # -------------------------------------------------

    def load(self, filename):

        self.filename = Path(filename)

        if not self.filename.exists():

            raise FileNotFoundError(
                self.filename
            )

        with open(
            self.filename,
            "r",
            encoding="utf-8"
        ) as f:

            self.recipe = json.load(f)

        recipe_name = self.recipe.get(
            "recipe_name",
            self.filename.stem
        )

        print(
            f"[INFO] Recipe yüklendi: {recipe_name}"
        )

    # -------------------------------------------------
    # Beklenen Durum
    # -------------------------------------------------

    def expected(
        self,
        roi_name
    ):

        return self.recipe.get(
            "regions",
            {}
        ).get(
            roi_name,
            "EMPTY"
        )

    # -------------------------------------------------
    # Recipe Yüklü mü?
    # -------------------------------------------------

    def is_loaded(self):

        return bool(self.recipe)

    # -------------------------------------------------
    # Recipe Adı
    # -------------------------------------------------

    def recipe_name(self):

        return self.recipe.get(
            "recipe_name",
            ""
        )