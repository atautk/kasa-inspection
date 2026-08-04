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
