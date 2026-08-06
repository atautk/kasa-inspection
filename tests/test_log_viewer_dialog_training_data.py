from pathlib import Path
from unittest.mock import patch

import pytest

from PySide6.QtWidgets import QMessageBox

from modules.configuration.band import Band
from modules.configuration.inspection_logger import InspectionLogger
from modules.configuration.training_data_manager import TrainingDataManager


@pytest.fixture(scope="module")
def qapp():

    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


@pytest.fixture
def band(tmp_path):

    b = Band(
        id="band_01",
        name="Test Bandı",
        root=tmp_path,
        reference=tmp_path / "reference.png",
        roi=tmp_path / "roi.json",
        models=tmp_path / "models"
    )
    b.root.mkdir(parents=True, exist_ok=True)

    return b


@pytest.fixture
def logger(band):

    return InspectionLogger(band)


@pytest.fixture
def dialog(qapp, logger, band):

    from modules.ui.inspection.log_viewer_dialog import LogViewerDialog

    d = LogViewerDialog(
        logger, band.name, operator_name="test", band=band
    )

    yield d

    d.close()


def _ng_result():

    return {
        "G01": {
            "state": "EMPTY", "expected": "FULL", "ok": False,
            "change_ratio": 0.1
        }
    }


def test_correcting_roi_flags_saved_training_images_for_review(
    dialog, logger, band
):

    training_manager = TrainingDataManager()

    import numpy as np

    saved = training_manager.save(
        band, "G01", "EMPTY",
        np.zeros((10, 10, 3), dtype="uint8"),
        np.zeros((10, 10, 3), dtype="uint8")
    )

    logger.log(_ng_result(), "clio", training_image_paths={"G01": saved})
    record_id = logger.last_inserted_id

    dialog.current_record = logger.fetch_recent(1)[0]
    dialog.current_roi_names = ["G01"]

    with patch.object(
        dialog.roi_detail_table, "selectedItems"
    ) as mock_selected:

        mock_item = type("Item", (), {"row": lambda self=None: 0})()
        mock_selected.return_value = [mock_item]

        with patch(
            "modules.ui.inspection.log_viewer_dialog.QMessageBox.question",
            return_value=QMessageBox.Yes
        ):

            dialog._on_correct_roi_clicked()

    flag_path = Path(saved["current"]).with_suffix(".flagged_for_review")
    assert flag_path.exists()


def test_correcting_roi_without_saved_training_images_does_not_error(
    dialog, logger
):

    logger.log(_ng_result(), "clio")

    dialog.current_record = logger.fetch_recent(1)[0]
    dialog.current_roi_names = ["G01"]

    with patch.object(
        dialog.roi_detail_table, "selectedItems"
    ) as mock_selected:

        mock_item = type("Item", (), {"row": lambda self=None: 0})()
        mock_selected.return_value = [mock_item]

        with patch(
            "modules.ui.inspection.log_viewer_dialog.QMessageBox.question",
            return_value=QMessageBox.Yes
        ):

            dialog._on_correct_roi_clicked()

    # hata firlatmadan tamamlanmis olmali - ayrica kayit gercekten
    # düzeltilmiş mi kontrol edelim
    corrected = logger.fetch_recent(1)[0]
    assert corrected["overall_result"] == "OK"
