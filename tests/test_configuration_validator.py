import json

import pytest

from modules.configuration.band_manager import BandManager
from modules.configuration.model_manager import ModelManager
from modules.configuration.configuration_validator import ConfigurationValidator


@pytest.fixture
def band_manager(tmp_path):

    return BandManager(root=tmp_path / "configuration")


@pytest.fixture
def validator():

    return ConfigurationValidator()


def _write_rois(band, names):

    band.roi.write_text(
        json.dumps({
            "version": "1.0",
            "rois": [
                {"id": str(i), "name": name, "points": [[0, 0], [1, 0], [1, 1]]}
                for i, name in enumerate(names)
            ]
        }),
        encoding="utf-8"
    )


def test_fresh_band_is_missing_reference_roi_and_models(band_manager, validator):

    band = band_manager.create_band("Clio Hattı")

    # yeni bandda roi.json var ama boş, reference yok, model yok
    band.reference.unlink(missing_ok=True)

    result = validator.validate(band)

    assert result["valid"] is False
    assert any("reference.png" in e for e in result["errors"])
    assert any("model" in e.lower() for e in result["errors"])


def test_fully_configured_band_is_valid(band_manager, validator):

    band = band_manager.create_band("Clio Hattı")

    band.reference.write_bytes(b"fake png")
    _write_rois(band, ["G01", "G02"])

    model = ModelManager().create_model(band, "Clio")
    model.expected_rois = ["G01"]
    ModelManager().save_model(band, model)

    result = validator.validate(band)

    assert result["valid"] is True
    assert result["errors"] == []


def test_duplicate_roi_id_is_flagged(band_manager, validator):

    band = band_manager.create_band("Clio Hattı")
    band.reference.write_bytes(b"fake png")

    band.roi.write_text(
        json.dumps({"version": "1.0", "rois": [
            {"id": "dup", "name": "G01", "points": [[0, 0], [1, 0], [1, 1]]},
            {"id": "dup", "name": "G02", "points": [[0, 0], [1, 0], [1, 1]]}
        ]}),
        encoding="utf-8"
    )

    ModelManager().create_model(band, "Clio")

    result = validator.validate(band)

    assert result["valid"] is False
    assert any("tekrar ediyor" in e for e in result["errors"])


def test_roi_with_too_few_points_is_flagged(band_manager, validator):

    band = band_manager.create_band("Clio Hattı")
    band.reference.write_bytes(b"fake png")

    band.roi.write_text(
        json.dumps({"version": "1.0", "rois": [
            {"id": "1", "name": "G01", "points": [[0, 0], [1, 0]]}
        ]}),
        encoding="utf-8"
    )

    ModelManager().create_model(band, "Clio")

    result = validator.validate(band)

    assert result["valid"] is False
    assert any("en az 3" in e for e in result["errors"])


def test_model_expecting_deleted_roi_is_flagged(band_manager, validator):

    band = band_manager.create_band("Clio Hattı")
    band.reference.write_bytes(b"fake png")

    _write_rois(band, ["G01", "G02"])

    model = ModelManager().create_model(band, "Clio")
    model.expected_rois = ["G01", "G99"]
    ModelManager().save_model(band, model)

    result = validator.validate(band)

    assert result["valid"] is False
    assert any("G99" in e for e in result["errors"])
