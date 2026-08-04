import pytest

from modules.configuration.band_manager import BandManager


@pytest.fixture
def manager(tmp_path):

    return BandManager(root=tmp_path / "configuration")


def test_create_band_assigns_sequential_ids(manager):

    first = manager.create_band("Clio Hattı")
    second = manager.create_band("Duster Hattı")

    assert first.id == "band_01"
    assert second.id == "band_02"


def test_create_band_writes_default_roi_and_band_json(manager):

    band = manager.create_band("Clio Hattı", camera=2)

    assert band.roi.exists()
    assert (band.root / "band.json").exists()
    assert band.models.is_dir()

    assert band.camera == 2
    assert band.threshold == 3.0
    assert band.arduino_port == ""


def test_save_and_load_roundtrip_preserves_settings(manager):

    band = manager.create_band("Clio Hattı")

    band.threshold = 7.5
    band.arduino_port = "COM7"
    band.name = "Clio Hattı v2"

    manager.save_band(band)

    reloaded = manager.load_band(band.id)

    assert reloaded.threshold == 7.5
    assert reloaded.arduino_port == "COM7"
    assert reloaded.name == "Clio Hattı v2"


def test_load_unknown_band_raises(manager):

    with pytest.raises(FileNotFoundError):
        manager.load_band("band_99")


def test_exists(manager):

    band = manager.create_band("Clio Hattı")

    assert manager.exists(band.id) is True
    assert manager.exists("band_99") is False


def test_delete_band(manager):

    band = manager.create_band("Clio Hattı")

    manager.delete_band(band.id)

    assert manager.exists(band.id) is False


def test_delete_unknown_band_does_not_raise(manager):

    manager.delete_band("band_99")


def test_list_bands_returns_all_created(manager):

    manager.create_band("Clio Hattı")
    manager.create_band("Duster Hattı")

    bands = manager.list_bands()

    assert [band.name for band in bands] == ["Clio Hattı", "Duster Hattı"]
