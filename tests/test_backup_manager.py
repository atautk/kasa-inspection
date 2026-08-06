import pytest

from modules.configuration.band import Band
from modules.configuration.backup_manager import BackupManager


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

    return BackupManager()


def test_backup_copies_db_and_ng_captures_without_deleting_originals(
    manager, band, tmp_path
):

    db_path = band.root / "inspection_log.db"
    db_path.write_bytes(b"fake sqlite content")

    ng_folder = band.root / "ng_captures"
    ng_folder.mkdir()
    (ng_folder / "photo1.png").write_bytes(b"fake png")

    destination = tmp_path / "backups"
    destination.mkdir()

    target = manager.backup_band(band, destination)

    assert (target / "inspection_log.db").read_bytes() == b"fake sqlite content"
    assert (target / "ng_captures" / "photo1.png").exists()

    # orijinaller hâlâ yerinde olmalı (yedekleme, temizlik değil)
    assert db_path.exists()
    assert (ng_folder / "photo1.png").exists()


def test_backup_with_no_db_or_ng_captures_does_not_raise(manager, band, tmp_path):

    destination = tmp_path / "backups"
    destination.mkdir()

    target = manager.backup_band(band, destination)

    assert target.exists()
    assert not (target / "inspection_log.db").exists()
    assert not (target / "ng_captures").exists()


def test_backup_target_is_named_with_band_and_timestamp(manager, band, tmp_path):

    destination = tmp_path / "backups"
    destination.mkdir()

    target = manager.backup_band(band, destination)

    assert target.name.startswith("Clio Hattı_yedek_")


def test_calling_backup_twice_in_a_row_does_not_raise(manager, band, tmp_path):

    destination = tmp_path / "backups"
    destination.mkdir()

    (band.root / "inspection_log.db").write_bytes(b"data")

    target1 = manager.backup_band(band, destination)
    target2 = manager.backup_band(band, destination)

    assert target1.exists() and target2.exists()


# -------------------------------------------------
# cleanup_old_backups / backup_and_cleanup
# -------------------------------------------------

def _make_backup_folder(destination, band_name, timestamp_suffix):

    folder = destination / f"{band_name}_yedek_{timestamp_suffix}"
    folder.mkdir()

    return folder


def test_cleanup_keeps_only_most_recent_n_backups(manager, band, tmp_path):

    destination = tmp_path / "backups"
    destination.mkdir()

    for suffix in [
        "20260101_000000", "20260102_000000",
        "20260103_000000", "20260104_000000"
    ]:
        _make_backup_folder(destination, band.name, suffix)

    manager.cleanup_old_backups(band, destination, keep_count=2)

    remaining = sorted(p.name for p in destination.iterdir())

    assert remaining == [
        f"{band.name}_yedek_20260103_000000",
        f"{band.name}_yedek_20260104_000000"
    ]


def test_cleanup_does_nothing_when_fewer_backups_than_keep_count(
    manager, band, tmp_path
):

    destination = tmp_path / "backups"
    destination.mkdir()

    _make_backup_folder(destination, band.name, "20260101_000000")

    manager.cleanup_old_backups(band, destination, keep_count=10)

    assert len(list(destination.iterdir())) == 1


def test_cleanup_does_nothing_when_keep_count_is_zero_or_negative(
    manager, band, tmp_path
):

    destination = tmp_path / "backups"
    destination.mkdir()

    _make_backup_folder(destination, band.name, "20260101_000000")

    manager.cleanup_old_backups(band, destination, keep_count=0)
    manager.cleanup_old_backups(band, destination, keep_count=-5)

    assert len(list(destination.iterdir())) == 1


def test_cleanup_does_not_touch_other_bands_backups(manager, band, tmp_path):

    destination = tmp_path / "backups"
    destination.mkdir()

    _make_backup_folder(destination, band.name, "20260101_000000")
    _make_backup_folder(destination, band.name, "20260102_000000")
    _make_backup_folder(destination, "Diğer Band", "20260101_000000")

    manager.cleanup_old_backups(band, destination, keep_count=1)

    remaining = sorted(p.name for p in destination.iterdir())

    assert remaining == sorted([
        "Diğer Band_yedek_20260101_000000",
        f"{band.name}_yedek_20260102_000000"
    ])


def test_cleanup_handles_missing_destination_gracefully(manager, band, tmp_path):

    manager.cleanup_old_backups(
        band, tmp_path / "does_not_exist", keep_count=5
    )


def test_backup_and_cleanup_creates_new_backup_and_prunes_old_ones(
    manager, band, tmp_path
):

    destination = tmp_path / "backups"
    destination.mkdir()

    for suffix in ["20260101_000000", "20260102_000000"]:
        _make_backup_folder(destination, band.name, suffix)

    (band.root / "inspection_log.db").write_bytes(b"data")

    target = manager.backup_and_cleanup(band, destination, keep_count=2)

    assert target.exists()

    remaining = list(destination.iterdir())
    assert len(remaining) == 2
    assert target in remaining
