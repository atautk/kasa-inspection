import json


class RecipeManager:

    def __init__(self):

        self.recipe = {}

    def load(self, filename):

        with open(filename, "r", encoding="utf-8") as f:

            self.recipe = json.load(f)

        print(
            "[INFO] Recipe yüklendi:",
            self.recipe["recipe_name"]
        )

    def expected(self, roi_name):

        return self.recipe["regions"].get(
            roi_name,
            "EMPTY"
        )