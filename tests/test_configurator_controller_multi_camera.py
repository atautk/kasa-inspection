import json

import numpy as np
import pytest


@pytest.fixture(scope="module")
def qapp():

    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


@pytest.fixture
def controller(qapp, tmp_path):

    from modules.ui.configurator.main_window import MainWindow
    from modules.ui.configurator.configurator_controller import (
        ConfiguratorController
    )
    from modules.configuration.band_manager import BandManager

    window = MainWindow()
    ctrl = ConfiguratorController(window, operator_name="test")

    # Gerçek configuration/ klasörüne asla dokunmamak için
    # band_manager'ı geçici bir köke yönlendiriyoruz.
    ctrl.band_manager = BandManager(root=tmp_path / "configuration")

    return ctrl


def _open_band(controller, name="Test Bandı"):

    controller.band_manager.create_band(name)
    controller.load_bands()

    item = controller.window.band_page.band_list.item(0)
    controller.window.band_page.band_list.setCurrentItem(item)

    controller.open_band()

    # open_band() bandı diskten yeniden yükler - controller.current_band,
    # create_band()'in döndürdüğü nesneden FARKLI bir örnektir. Testler
    # bu yüzden her zaman current_band üzerinde çalışmalı.
    return controller.current_band


def test_camera_targets_starts_with_primary_only(controller):

    _open_band(controller)

    targets = controller._camera_targets()

    assert len(targets) == 1
    assert targets[0][0] == "Birincil Kamera"
    assert targets[0][1] is None
    assert targets[0][2] is controller.current_band


def test_camera_targets_includes_added_channels(controller):

    band = _open_band(controller)

    channel = controller.band_manager.add_camera_channel(
        band, "Yan", camera_index=1
    )

    targets = controller._camera_targets()

    assert len(targets) == 2
    assert targets[1] == ("Yan", channel.id, channel)


def test_camera_target_by_id_falls_back_to_primary(controller):

    _open_band(controller)

    target = controller._camera_target_by_id("does-not-exist")

    assert target is controller.current_band


def test_camera_index_of_band_uses_camera_field(controller):

    band = _open_band(controller)
    band.camera = 3

    assert controller._camera_index_of(band) == 3


def test_camera_index_of_channel_uses_camera_index_field(controller):

    band = _open_band(controller)

    channel = controller.band_manager.add_camera_channel(
        band, "Yan", camera_index=2
    )

    assert controller._camera_index_of(channel) == 2


def test_reference_capture_is_isolated_per_channel(controller):

    band = _open_band(controller)

    channel = controller.band_manager.add_camera_channel(
        band, "Yan", camera_index=1
    )

    controller._refresh_camera_selectors()

    # Birincil kamera için referans çek
    controller.last_reference_frame = np.zeros(
        (480, 640, 3), dtype=np.uint8
    )
    controller.capture_reference()

    assert controller.reference_manager.exists(band)

    # "Yan" kanalına geç ve onun için de referans çek
    page = controller.window.reference_page
    index = page.channel_combo.findData(channel.id)
    page.channel_combo.setCurrentIndex(index)
    controller.on_reference_channel_changed()

    controller.last_reference_frame = np.full(
        (480, 640, 3), 50, dtype=np.uint8
    )
    controller.capture_reference()

    assert controller.reference_manager.exists(channel)

    primary_image = controller.reference_manager.load(band)
    channel_image = controller.reference_manager.load(channel)

    assert primary_image.mean() != channel_image.mean()


def test_roi_save_is_isolated_per_channel(controller):

    band = _open_band(controller)

    channel = controller.band_manager.add_camera_channel(
        band, "Yan", camera_index=1
    )

    controller._refresh_camera_selectors()

    page = controller.window.roi_page
    index = page.channel_combo.findData(channel.id)
    page.channel_combo.setCurrentIndex(index)
    controller.on_roi_channel_changed()

    page.load_rois([
        {"id": "", "name": "G01", "points": [[0, 0], [10, 0], [10, 10]]}
    ])

    controller.save_rois()

    channel_roi_data = json.loads(
        channel.roi.read_text(encoding="utf-8")
    )
    primary_roi_data = json.loads(
        band.roi.read_text(encoding="utf-8")
    )

    assert channel_roi_data["rois"][0]["name"] == "G01"
    assert primary_roi_data["rois"] == []


def test_roi_names_includes_qualified_extra_channel_names(controller):

    band = _open_band(controller)

    channel = controller.band_manager.add_camera_channel(
        band, "Yan", camera_index=1
    )

    with open(band.roi, "w", encoding="utf-8") as f:
        json.dump(
            {"version": "1.0", "rois": [{"name": "G01", "points": []}]},
            f
        )

    with open(channel.roi, "w", encoding="utf-8") as f:
        json.dump(
            {"version": "1.0", "rois": [{"name": "G01", "points": []}]},
            f
        )

    names = controller._roi_names()

    assert "G01" in names
    assert "Yan:G01" in names


def test_remove_camera_channel_removes_it_from_targets(controller):

    band = _open_band(controller)

    channel = controller.band_manager.add_camera_channel(
        band, "Yan", camera_index=1
    )

    controller.band_manager.remove_camera_channel(band, channel.id)

    targets = controller._camera_targets()

    assert len(targets) == 1
