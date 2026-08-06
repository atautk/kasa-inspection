import pytest

from modules.configuration.band_manager import BandManager
from modules.configuration.model_manager import ModelManager


@pytest.fixture
def band(tmp_path):

    return BandManager(root=tmp_path / "configuration").create_band("Clio Hattı")


@pytest.fixture
def manager():

    return ModelManager()


def test_create_model_slugifies_id(manager, band):

    model = manager.create_model(band, "Clio 1.6 Dizel")

    assert model.id == "clio_1_6_dizel"
    assert model.expected_rois == []


def test_save_and_load_roundtrip_preserves_expected_rois(manager, band):

    model = manager.create_model(band, "Clio")

    model.expected_rois = ["G01", "G03", "G05"]
    manager.save_model(band, model)

    reloaded = manager.load_model(band, model.id)

    assert reloaded.expected_rois == ["G01", "G03", "G05"]
    assert reloaded.name == "Clio"


def test_create_model_starts_with_no_threshold_overrides(manager, band):

    model = manager.create_model(band, "Clio")

    assert model.roi_thresholds == {}


def test_save_and_load_roundtrip_preserves_roi_thresholds(manager, band):

    model = manager.create_model(band, "Clio")

    model.roi_thresholds = {"G01": 12.5, "G03": 1.0}
    manager.save_model(band, model)

    reloaded = manager.load_model(band, model.id)

    assert reloaded.roi_thresholds == {"G01": 12.5, "G03": 1.0}


def test_load_model_without_roi_thresholds_field_defaults_to_empty(
    manager, band
):

    # Bu alan eklenmeden önce kaydedilmiş eski bir model.json'u simüle et
    import json

    file = band.models / "eski.json"
    file.write_text(
        json.dumps({
            "id": "eski", "name": "Eski Model", "version": "1.0",
            "expected_rois": ["G01"]
        }),
        encoding="utf-8"
    )

    model = manager.load_model(band, "eski")

    assert model.roi_thresholds == {}


def test_create_model_has_no_marker_id_by_default(manager, band):

    model = manager.create_model(band, "Clio")

    assert model.marker_id is None


def test_save_and_load_roundtrip_preserves_marker_id(manager, band):

    model = manager.create_model(band, "Clio")

    model.marker_id = 4
    manager.save_model(band, model)

    reloaded = manager.load_model(band, model.id)

    assert reloaded.marker_id == 4


def test_load_model_without_marker_id_field_defaults_to_none(manager, band):

    import json

    file = band.models / "eski.json"
    file.write_text(
        json.dumps({
            "id": "eski", "name": "Eski Model", "version": "1.0",
            "expected_rois": ["G01"], "roi_thresholds": {}
        }),
        encoding="utf-8"
    )

    model = manager.load_model(band, "eski")

    assert model.marker_id is None


def test_load_missing_model_raises(manager, band):

    with pytest.raises(FileNotFoundError):
        manager.load_model(band, "yok")


def test_list_models_skips_unreadable_files(manager, band):

    manager.create_model(band, "Clio")
    manager.create_model(band, "Duster")

    (band.models / "bozuk.json").write_text("not valid json", encoding="utf-8")

    models = manager.list_models(band)

    assert sorted(m.name for m in models) == ["Clio", "Duster"]


def test_delete_model(manager, band):

    model = manager.create_model(band, "Clio")

    manager.delete_model(band, model.id)

    assert manager.list_models(band) == []


def test_delete_missing_model_does_not_raise(manager, band):

    manager.delete_model(band, "yok")
