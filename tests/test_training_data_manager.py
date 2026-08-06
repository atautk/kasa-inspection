import numpy as np

from modules.configuration.band import Band
from modules.configuration.training_data_manager import TrainingDataManager


def _band(tmp_path):

    return Band(
        id="band_01",
        name="Test Bandı",
        root=tmp_path,
        reference=tmp_path / "reference.png",
        roi=tmp_path / "roi.json",
        models=tmp_path / "models"
    )


def _crop():

    return np.zeros((30, 30, 3), dtype=np.uint8)


def test_save_creates_reference_and_current_files(tmp_path):

    manager = TrainingDataManager()
    band = _band(tmp_path)

    result = manager.save(band, "G01", "FULL", _crop(), _crop())

    assert result is not None
    assert result["reference"].endswith("_reference.png")
    assert result["current"].endswith("_current.png")

    from pathlib import Path
    assert Path(result["reference"]).exists()
    assert Path(result["current"]).exists()


def test_save_uses_roi_and_state_as_folder_structure(tmp_path):

    manager = TrainingDataManager()
    band = _band(tmp_path)

    result = manager.save(band, "G01", "FULL", _crop(), _crop())

    from pathlib import Path
    current_path = Path(result["current"])

    assert current_path.parent.name == "FULL"
    assert current_path.parent.parent.name == "G01"
    assert current_path.parent.parent.parent.name == "training_data"


def test_save_with_none_crop_returns_none(tmp_path):

    manager = TrainingDataManager()
    band = _band(tmp_path)

    assert manager.save(band, "G01", "FULL", None, _crop()) is None
    assert manager.save(band, "G01", "FULL", _crop(), None) is None


def test_save_avoids_filename_collision(tmp_path):

    manager = TrainingDataManager()
    band = _band(tmp_path)

    first = manager.save(band, "G01", "FULL", _crop(), _crop())
    second = manager.save(band, "G01", "FULL", _crop(), _crop())

    assert first["current"] != second["current"]


def test_different_states_go_to_different_folders(tmp_path):

    manager = TrainingDataManager()
    band = _band(tmp_path)

    full_result = manager.save(band, "G01", "FULL", _crop(), _crop())
    empty_result = manager.save(band, "G01", "EMPTY", _crop(), _crop())

    from pathlib import Path
    assert Path(full_result["current"]).parent != Path(empty_result["current"]).parent


def test_flag_for_review_creates_marker_file(tmp_path):

    manager = TrainingDataManager()
    band = _band(tmp_path)

    result = manager.save(band, "G01", "FULL", _crop(), _crop())

    manager.flag_for_review(result)

    from pathlib import Path
    flag_path = Path(result["current"]).with_suffix(".flagged_for_review")
    assert flag_path.exists()


def test_flag_for_review_handles_empty_input_gracefully(tmp_path):

    manager = TrainingDataManager()

    manager.flag_for_review(None)
    manager.flag_for_review({})


def test_clear_removes_training_data_folder(tmp_path):

    manager = TrainingDataManager()
    band = _band(tmp_path)

    manager.save(band, "G01", "FULL", _crop(), _crop())

    manager.clear(band)

    assert not (band.root / TrainingDataManager.FOLDER_NAME).exists()
