from __future__ import annotations

import json

from .band import Band
from .model_manager import ModelManager


class ConfigurationValidator:

    def __init__(self):

        self.model_manager = ModelManager()

    # -------------------------------------------------

    def validate(self, band: Band):

        errors = []

        roi_names = None

        # band.json

        if not (band.root / "band.json").exists():

            errors.append("band.json bulunamadı.")

        # reference

        if not band.reference.exists():

            errors.append("reference.png bulunamadı.")

        # roi

        if not band.roi.exists():

            errors.append("roi.json bulunamadı.")

        else:

            try:

                with open(
                    band.roi,
                    "r",
                    encoding="utf-8"
                ) as f:

                    roi_data = json.load(f)

            except Exception:

                errors.append("roi.json okunamadı.")

                roi_data = None

            if roi_data:

                errors.extend(
                    self._validate_rois(
                        roi_data
                    )
                )

                roi_names = {
                    roi.get("name", "")
                    for roi in roi_data.get("rois", [])
                }

        # models

        models = self.model_manager.list_models(
            band
        )

        if len(models) == 0:

            errors.append(
                "Hiç model oluşturulmamış."
            )

        if roi_names is not None:

            errors.extend(
                self._validate_model_rois(
                    models,
                    roi_names
                )
            )

        return {

            "valid": len(errors) == 0,

            "errors": errors

        }

    # -------------------------------------------------

    def _validate_model_rois(self, models, roi_names: set):

        errors = []

        for model in models:

            for roi_name in model.expected_rois:

                if roi_name not in roi_names:

                    errors.append(
                        f"{model.name}: '{roi_name}' ROI'si "
                        "roi.json'da bulunamadı (silinmiş/yeniden "
                        "adlandırılmış olabilir)."
                    )

        return errors

    # -------------------------------------------------

    def _validate_rois(
        self,
        roi_data
    ):

        errors = []

        ids = set()

        for roi in roi_data.get(
            "rois",
            []
        ):

            roi_id = roi.get("id")

            if roi_id in ids:

                errors.append(
                    f"{roi_id} tekrar ediyor."
                )

            ids.add(roi_id)

            points = roi.get(
                "points",
                []
            )

            if len(points) < 3:

                errors.append(
                    f"{roi_id} en az 3 noktaya sahip olmalı."
                )

        return errors