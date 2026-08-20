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


def test_new_band_has_no_shift_windows_by_default(manager):

    band = manager.create_band("Clio Hattı")

    assert band.shifts == []


def test_add_shift_appends_and_persists(manager):

    band = manager.create_band("Clio Hattı")

    shift = manager.add_shift(band, "Sabah", "07:30", "15:30")

    assert shift.name == "Sabah"
    assert shift.start == "07:30"
    assert shift.end == "15:30"
    assert shift.operator == ""
    assert shift in band.shifts

    reloaded = manager.load_band(band.id)

    assert len(reloaded.shifts) == 1
    assert reloaded.shifts[0].name == "Sabah"
    assert reloaded.shifts[0].start == "07:30"
    assert reloaded.shifts[0].end == "15:30"
    assert reloaded.shifts[0].operator == ""


def test_add_shift_with_operator_persists(manager):

    band = manager.create_band("Clio Hattı")

    shift = manager.add_shift(band, "Sabah", "07:30", "15:30", "Ahmet Yılmaz")

    assert shift.operator == "Ahmet Yılmaz"

    reloaded = manager.load_band(band.id)

    assert reloaded.shifts[0].operator == "Ahmet Yılmaz"


def test_update_shift_changes_fields_and_persists(manager):

    band = manager.create_band("Clio Hattı")

    shift = manager.add_shift(band, "Sabah", "07:30", "15:30")

    manager.update_shift(
        band, shift.id, "Sabah Vardiyası", "08:00", "16:00", "Ahmet Yılmaz"
    )

    assert band.shifts[0].name == "Sabah Vardiyası"
    assert band.shifts[0].start == "08:00"
    assert band.shifts[0].end == "16:00"
    assert band.shifts[0].operator == "Ahmet Yılmaz"

    reloaded = manager.load_band(band.id)

    assert reloaded.shifts[0].name == "Sabah Vardiyası"
    assert reloaded.shifts[0].start == "08:00"
    assert reloaded.shifts[0].end == "16:00"
    assert reloaded.shifts[0].operator == "Ahmet Yılmaz"


def test_remove_shift(manager):

    band = manager.create_band("Clio Hattı")

    shift = manager.add_shift(band, "Sabah", "07:30", "15:30")
    manager.add_shift(band, "Gece", "22:00", "06:00")

    manager.remove_shift(band, shift.id)

    assert len(band.shifts) == 1
    assert band.shifts[0].name == "Gece"

    reloaded = manager.load_band(band.id)

    assert len(reloaded.shifts) == 1


def test_load_band_without_shifts_field_defaults_to_empty_list(manager):

    import json

    band = manager.create_band("Eski Band")

    data = json.loads((band.root / "band.json").read_text(encoding="utf-8"))
    assert "shifts" not in data

    reloaded = manager.load_band(band.id)

    assert reloaded.shifts == []


def test_new_band_has_default_blur_threshold(manager):

    band = manager.create_band("Clio Hattı")

    assert band.blur_threshold == 100.0


def test_blur_threshold_save_and_load_roundtrip(manager):

    band = manager.create_band("Clio Hattı")

    band.blur_threshold = 150.0

    manager.save_band(band)

    reloaded = manager.load_band(band.id)

    assert reloaded.blur_threshold == 150.0


def test_load_band_without_blur_threshold_field_defaults(manager):

    import json

    band = manager.create_band("Eski Band")

    data = json.loads((band.root / "band.json").read_text(encoding="utf-8"))
    assert "blur_threshold" not in data

    reloaded = manager.load_band(band.id)

    assert reloaded.blur_threshold == 100.0


def test_new_band_has_reference_reminder_disabled_by_default(manager):

    band = manager.create_band("Clio Hattı")

    assert band.reference_max_age_days == 0


def test_reference_max_age_days_save_and_load_roundtrip(manager):

    band = manager.create_band("Clio Hattı")

    band.reference_max_age_days = 30

    manager.save_band(band)

    reloaded = manager.load_band(band.id)

    assert reloaded.reference_max_age_days == 30


def test_load_band_without_reference_max_age_days_field_defaults(manager):

    import json

    band = manager.create_band("Eski Band")

    data = json.loads((band.root / "band.json").read_text(encoding="utf-8"))
    assert "reference_max_age_days" not in data

    reloaded = manager.load_band(band.id)

    assert reloaded.reference_max_age_days == 0


def test_new_band_has_training_data_collection_disabled_by_default(manager):

    band = manager.create_band("Clio Hattı")

    assert band.training_data_collection_enabled is False


def test_training_data_collection_enabled_save_and_load_roundtrip(manager):

    band = manager.create_band("Clio Hattı")

    band.training_data_collection_enabled = True

    manager.save_band(band)

    reloaded = manager.load_band(band.id)

    assert reloaded.training_data_collection_enabled is True


def test_load_band_without_training_data_collection_field_defaults(manager):

    import json

    band = manager.create_band("Eski Band")

    data = json.loads((band.root / "band.json").read_text(encoding="utf-8"))
    assert "training_data_collection_enabled" not in data

    reloaded = manager.load_band(band.id)

    assert reloaded.training_data_collection_enabled is False


def test_new_band_has_auto_backup_disabled_by_default(manager):

    band = manager.create_band("Clio Hattı")

    assert band.auto_backup_enabled is False
    assert band.auto_backup_destination == ""
    assert band.auto_backup_interval_hours == 24.0
    assert band.auto_backup_keep_count == 30
    assert band.last_auto_backup_at == ""


def test_auto_backup_settings_save_and_load_roundtrip(manager):

    band = manager.create_band("Clio Hattı")

    band.auto_backup_enabled = True
    band.auto_backup_destination = "D:/yedekler"
    band.auto_backup_interval_hours = 12.0
    band.auto_backup_keep_count = 10
    band.last_auto_backup_at = "2026-08-06T10:00:00+00:00"

    manager.save_band(band)

    reloaded = manager.load_band(band.id)

    assert reloaded.auto_backup_enabled is True
    assert reloaded.auto_backup_destination == "D:/yedekler"
    assert reloaded.auto_backup_interval_hours == 12.0
    assert reloaded.auto_backup_keep_count == 10
    assert reloaded.last_auto_backup_at == "2026-08-06T10:00:00+00:00"


def test_load_band_without_auto_backup_fields_defaults(manager):

    import json

    band = manager.create_band("Eski Band")

    data = json.loads((band.root / "band.json").read_text(encoding="utf-8"))
    assert "auto_backup_enabled" not in data

    reloaded = manager.load_band(band.id)

    assert reloaded.auto_backup_enabled is False
    assert reloaded.auto_backup_keep_count == 30


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
