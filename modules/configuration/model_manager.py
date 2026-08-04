from __future__ import annotations

import json
import re

from .model import Model
from .band import Band


class ModelManager:

    # -----------------------------------------
    # Model Listesi
    # -----------------------------------------

    def list_models(
        self,
        band: Band
    ) -> list[Model]:

        models = []

        for file in sorted(band.models.glob("*.json")):

            try:

                models.append(
                    self.load_model(
                        band,
                        file.stem
                    )
                )

            except Exception:

                pass

        return models

    # -----------------------------------------
    # Model Yükle
    # -----------------------------------------

    def load_model(
        self,
        band: Band,
        model_id: str
    ) -> Model:

        file = band.models / f"{model_id}.json"

        if not file.exists():

            raise FileNotFoundError(file)

        with open(
            file,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        return Model(

            id=data["id"],

            name=data["name"],

            expected_rois=data.get(
                "expected_rois",
                []
            ),

            version=data.get(
                "version",
                "1.0"
            ),

            roi_thresholds=data.get(
                "roi_thresholds",
                {}
            )

        )

    # -----------------------------------------
    # Model Kaydet
    # -----------------------------------------

    def save_model(
        self,
        band: Band,
        model: Model
    ):

        file = band.models / f"{model.id}.json"

        data = {

            "id": model.id,

            "name": model.name,

            "version": model.version,

            "expected_rois": model.expected_rois,

            "roi_thresholds": model.roi_thresholds

        }

        with open(
            file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )

    # -----------------------------------------
    # Yeni Model
    # -----------------------------------------

    def create_model(
        self,
        band: Band,
        name: str
    ) -> Model:

        model_id = re.sub(r"[^a-z0-9_-]", "_", name.strip().lower().replace(" ", "_"))

        model = Model(

            id=model_id,

            name=name,

            expected_rois=[]

        )

        self.save_model(
            band,
            model
        )

        return model

    # -----------------------------------------
    # Model Sil
    # -----------------------------------------

    def delete_model(
        self,
        band: Band,
        model_id: str
    ):

        file = band.models / f"{model_id}.json"

        if file.exists():

            file.unlink()