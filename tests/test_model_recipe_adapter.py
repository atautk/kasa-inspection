from modules.configuration.model import Model
from modules.configuration.model_recipe_adapter import ModelRecipeAdapter


def _model(expected_rois=None, roi_thresholds=None):

    return Model(
        id="clio",
        name="Clio",
        expected_rois=expected_rois or [],
        roi_thresholds=roi_thresholds or {}
    )


def test_no_model_treats_everything_as_empty_and_no_threshold_override():

    adapter = ModelRecipeAdapter(None)

    assert adapter.expected("G01") == "EMPTY"
    assert adapter.threshold_for("G01") is None
    assert adapter.is_loaded() is False
    assert adapter.recipe_name() == ""


def test_expected_roi_is_full_others_are_empty():

    adapter = ModelRecipeAdapter(_model(expected_rois=["G01", "G03"]))

    assert adapter.expected("G01") == "FULL"
    assert adapter.expected("G02") == "EMPTY"
    assert adapter.expected("G03") == "FULL"


def test_threshold_for_returns_override_when_set():

    adapter = ModelRecipeAdapter(
        _model(roi_thresholds={"G01": 12.5})
    )

    assert adapter.threshold_for("G01") == 12.5


def test_threshold_for_returns_none_when_not_overridden():

    adapter = ModelRecipeAdapter(
        _model(roi_thresholds={"G01": 12.5})
    )

    assert adapter.threshold_for("G02") is None


def test_is_loaded_and_recipe_name():

    adapter = ModelRecipeAdapter(_model())

    assert adapter.is_loaded() is True
    assert adapter.recipe_name() == "Clio"
