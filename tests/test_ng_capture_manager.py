import numpy as np
import pytest

from modules.configuration.band import Band
from modules.configuration.ng_capture_manager import NGCaptureManager


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

    return NGCaptureManager()


def test_save_writes_image_file(manager, band):

    image = np.zeros((10, 10, 3), dtype=np.uint8)

    path = manager.save(band, image)

    assert path is not None
    assert (band.root / "ng_captures").is_dir()

    from pathlib import Path
    assert Path(path).exists()


def test_save_none_image_returns_none(manager, band):

    assert manager.save(band, None) is None
    assert not (band.root / "ng_captures").exists()


def test_multiple_saves_produce_distinct_files(manager, band):

    image = np.zeros((10, 10, 3), dtype=np.uint8)

    path1 = manager.save(band, image)
    path2 = manager.save(band, image)

    assert path1 != path2


def test_clear_removes_folder(manager, band):

    image = np.zeros((10, 10, 3), dtype=np.uint8)
    manager.save(band, image)

    manager.clear(band)

    assert not (band.root / "ng_captures").exists()


def test_clear_on_missing_folder_does_not_raise(manager, band):

    manager.clear(band)
