from modules.configuration.model import Model
from modules.configuration.model_recipe_adapter import (
    ModelRecipeAdapter,
    PrefixedRecipeAdapter
)


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


def test_prefixed_adapter_qualifies_expected_lookup():

    base = ModelRecipeAdapter(_model(expected_rois=["Yan:G01"]))
    prefixed = PrefixedRecipeAdapter(base, "Yan")

    assert prefixed.expected("G01") == "FULL"
    assert prefixed.expected("G02") == "EMPTY"


def test_prefixed_adapter_does_not_leak_across_channels():

    base = ModelRecipeAdapter(_model(expected_rois=["Yan:G01"]))

    yan = PrefixedRecipeAdapter(base, "Yan")
    ust = PrefixedRecipeAdapter(base, "Üst")

    # ayni isimli (G01) ROI iki farkli kanalda var ama sadece
    # Yan:G01 beklenen listede - Üst kanalindaki G01 ile karismamali
    assert yan.expected("G01") == "FULL"
    assert ust.expected("G01") == "EMPTY"


def test_prefixed_adapter_qualifies_threshold_lookup():

    base = ModelRecipeAdapter(_model(roi_thresholds={"Yan:G01": 9.5}))
    prefixed = PrefixedRecipeAdapter(base, "Yan")

    assert prefixed.threshold_for("G01") == 9.5
    assert prefixed.threshold_for("G02") is None


def test_prefixed_adapter_delegates_is_loaded_and_recipe_name():

    base = ModelRecipeAdapter(_model())
    prefixed = PrefixedRecipeAdapter(base, "Yan")

    assert prefixed.is_loaded() is True
    assert prefixed.recipe_name() == "Clio"

    empty_base = ModelRecipeAdapter(None)
    empty_prefixed = PrefixedRecipeAdapter(empty_base, "Yan")

    assert empty_prefixed.is_loaded() is False
