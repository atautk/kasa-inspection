import json
import zipfile

import pytest

from modules.configuration.band_manager import BandManager
from modules.configuration.model_manager import ModelManager
from modules.configuration.band_export_manager import BandExportManager


@pytest.fixture
def band_manager(tmp_path):

    return BandManager(root=tmp_path / "configuration")


@pytest.fixture
def source_band(band_manager):

    band = band_manager.create_band("Clio Hattı", camera=1)

    band.threshold = 5.5
    band_manager.save_band(band)

    band.roi.write_text(
        json.dumps({"version": "1.0", "rois": [
            {"id": "1", "name": "G01", "points": [[0, 0], [1, 0], [1, 1]]}
        ]}),
        encoding="utf-8"
    )

    band.reference.write_bytes(b"fake png bytes")

    ModelManager().create_model(band, "Clio")

    # dışa aktarımda dahil edilmemesi gereken dosyalar
    (band.root / "inspection_log.db").write_bytes(b"should not be exported")

    ng = band.root / "ng_captures"
    ng.mkdir()
    (ng / "photo.png").write_bytes(b"should not be exported")

    return band


@pytest.fixture
def exporter():

    return BandExportManager()


def test_export_zip_contains_expected_entries_only(
    exporter, source_band, tmp_path
):

    destination = tmp_path / "export.zip"

    exporter.export_band(source_band, destination)

    with zipfile.ZipFile(destination, "r") as zf:
        names = set(zf.namelist())

    assert names == {
        "band.json", "roi.json", "reference.png", "models/clio.json"
    }
    assert "inspection_log.db" not in names
    assert not any(n.startswith("ng_captures/") for n in names)


def test_import_creates_new_band_with_matching_content(
    exporter, source_band, band_manager, tmp_path
):

    destination = tmp_path / "export.zip"
    exporter.export_band(source_band, destination)

    imported = exporter.import_band(band_manager, destination)

    assert imported.id != source_band.id
    assert imported.name == "Clio Hattı"
    assert imported.threshold == 5.5

    assert imported.roi.read_text(encoding="utf-8") == source_band.roi.read_text(
        encoding="utf-8"
    )
    assert imported.reference.read_bytes() == b"fake png bytes"
    assert (imported.models / "clio.json").exists()

    # inspection geçmişi asla içe/dışa aktarılmamalı
    assert not (imported.root / "inspection_log.db").exists()
    assert not (imported.root / "ng_captures").exists()


def test_import_rejects_zip_without_band_json(exporter, band_manager, tmp_path):

    bad_zip = tmp_path / "bad.zip"

    with zipfile.ZipFile(bad_zip, "w") as zf:
        zf.writestr("roi.json", "{}")

    with pytest.raises(ValueError):
        exporter.import_band(band_manager, bad_zip)
