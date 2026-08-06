import json
from pathlib import Path

import numpy as np
import pytest

from modules.configuration.band import Band
from modules.configuration.unknown_kasa_capture_manager import (
    UnknownKasaCaptureManager
)


@pytest.fixture
def band(tmp_path):

    root = tmp_path / "band_01"
    root.mkdir()

    return Band(
        id="band_01",
        name="Clio Hattı",
        root=root,
        reference=root / "reference.png",
        roi=root / "roi.json",
        models=root / "models"
    )


@pytest.fixture
def manager():

    return UnknownKasaCaptureManager()


def _image():
    return np.zeros((10, 10, 3), dtype=np.uint8)


def test_save_writes_image_and_json_sidecar(manager, band):

    path = manager.save(
        band, _image(), marker_id=7,
        roi_states={"G01": "FULL", "G02": "EMPTY"}
    )

    assert path is not None
    assert (band.root / "unknown_kasa_captures").is_dir()
    assert Path(path).exists()

    sidecar = Path(path).with_suffix(".json")
    assert sidecar.exists()

    metadata = json.loads(sidecar.read_text(encoding="utf-8"))
    assert metadata["marker_id"] == 7
    assert metadata["roi_states"] == {"G01": "FULL", "G02": "EMPTY"}
    assert "timestamp" in metadata


def test_save_none_image_returns_none(manager, band):

    assert manager.save(band, None, marker_id=7, roi_states={}) is None
    assert not (band.root / "unknown_kasa_captures").exists()


def test_multiple_saves_produce_distinct_files(manager, band):

    path1 = manager.save(band, _image(), marker_id=7, roi_states={})
    path2 = manager.save(band, _image(), marker_id=7, roi_states={})

    assert path1 != path2
    assert Path(path1).with_suffix(".json").exists()
    assert Path(path2).with_suffix(".json").exists()


def test_filename_includes_marker_id(manager, band):

    path = manager.save(band, _image(), marker_id=42, roi_states={})

    assert "marker42" in Path(path).name


def test_clear_removes_folder(manager, band):

    manager.save(band, _image(), marker_id=7, roi_states={})

    manager.clear(band)

    assert not (band.root / "unknown_kasa_captures").exists()


def test_clear_on_missing_folder_does_not_raise(manager, band):

    manager.clear(band)
