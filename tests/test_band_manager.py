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
    assert band.confirm_frames == 3


def test_save_and_load_roundtrip_preserves_settings(manager):

    band = manager.create_band("Clio Hattı")

    band.threshold = 7.5
    band.arduino_port = "COM7"
    band.name = "Clio Hattı v2"
    band.confirm_frames = 5

    manager.save_band(band)

    reloaded = manager.load_band(band.id)

    assert reloaded.threshold == 7.5
    assert reloaded.arduino_port == "COM7"
    assert reloaded.name == "Clio Hattı v2"
    assert reloaded.confirm_frames == 5


def test_load_band_without_confirm_frames_field_defaults_to_three(
    manager, tmp_path
):

    # Bu alan eklenmeden önce kaydedilmiş eski bir band.json'u simüle et
    import json

    band = manager.create_band("Eski Band")

    data = json.loads((band.root / "band.json").read_text(encoding="utf-8"))
    del data["confirm_frames"]
    (band.root / "band.json").write_text(
        json.dumps(data), encoding="utf-8"
    )

    reloaded = manager.load_band(band.id)

    assert reloaded.confirm_frames == 3


def test_new_band_has_no_extra_camera_channels(manager):

    band = manager.create_band("Clio Hattı")

    assert band.cameras == []


def test_add_camera_channel_creates_files_and_appends(manager):

    band = manager.create_band("Clio Hattı")

    channel = manager.add_camera_channel(band, "Yan", camera_index=1)

    assert channel.name == "Yan"
    assert channel.camera_index == 1
    assert channel.roi.exists()
    assert not channel.reference.exists()  # henüz fotoğraf çekilmedi
    assert channel in band.cameras
    assert len(band.cameras) == 1


def test_add_camera_channel_persists_across_reload(manager):

    band = manager.create_band("Clio Hattı")
    manager.add_camera_channel(band, "Yan", camera_index=1)
    manager.add_camera_channel(band, "Üst", camera_index=2)

    reloaded = manager.load_band(band.id)

    assert len(reloaded.cameras) == 2
    names = {channel.name for channel in reloaded.cameras}
    assert names == {"Yan", "Üst"}

    for channel in reloaded.cameras:
        assert channel.roi.exists()
        assert channel.reference.parent == channel.roi.parent


def test_each_camera_channel_gets_its_own_roi_file(manager):

    band = manager.create_band("Clio Hattı")

    channel1 = manager.add_camera_channel(band, "Yan", camera_index=1)
    channel2 = manager.add_camera_channel(band, "Üst", camera_index=2)

    assert channel1.roi != channel2.roi
    assert channel1.roi.parent != channel2.roi.parent


def test_remove_camera_channel(manager):

    band = manager.create_band("Clio Hattı")

    channel = manager.add_camera_channel(band, "Yan", camera_index=1)
    manager.add_camera_channel(band, "Üst", camera_index=2)

    manager.remove_camera_channel(band, channel.id)

    assert len(band.cameras) == 1
    assert band.cameras[0].name == "Üst"

    reloaded = manager.load_band(band.id)
    assert len(reloaded.cameras) == 1


def test_remove_unknown_camera_channel_does_not_raise(manager):

    band = manager.create_band("Clio Hattı")

    manager.remove_camera_channel(band, "does-not-exist")

    assert band.cameras == []


def test_legacy_band_json_without_cameras_field_loads_empty_list(manager):

    import json

    band = manager.create_band("Eski Band")

    # create_band() zaten "cameras" anahtarı yazmıyor (tek kameralı
    # eski formatla birebir aynı) - bunun sorunsuz yüklendiğini
    # doğrula.
    data = json.loads((band.root / "band.json").read_text(encoding="utf-8"))
    assert "cameras" not in data

    reloaded = manager.load_band(band.id)

    assert reloaded.cameras == []
    # birincil kamera (geriye dönük uyumluluk) hâlâ çalışıyor
    assert reloaded.reference == band.root / "reference.png"
    assert reloaded.roi == band.root / "roi.json"


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
