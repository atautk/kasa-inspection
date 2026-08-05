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


def _frame():

    return np.zeros((480, 640, 3), dtype=np.uint8)


def test_reference_page_preview_rescales_on_window_resize(qapp):

    from modules.ui.configurator.reference_page import ReferencePage

    page = ReferencePage()
    page.resize(400, 300)
    page.show()

    page.set_preview(_frame())

    small_width = page.preview_label.pixmap().width()

    page.resize(1200, 900)
    qapp.processEvents()

    large_width = page.preview_label.pixmap().width()

    assert large_width > small_width


def test_reference_page_clear_preview_stops_rescaling(qapp):

    from modules.ui.configurator.reference_page import ReferencePage

    page = ReferencePage()
    page.show()

    page.set_preview(_frame())
    page.clear_preview()

    # clear_preview()'dan sonra resizeEvent artık eski kareyi tekrar
    # çizmeye çalışmamalı (pixmap None kalmalı).
    page.resize(800, 600)
    qapp.processEvents()

    assert page.preview_label.pixmap().isNull()


def test_inspection_page_image_rescales_on_window_resize(qapp):

    from modules.ui.inspection.inspection_page import InspectionPage

    page = InspectionPage()
    page.resize(400, 300)
    page.show()

    page.set_image(_frame())

    small_width = page.image_label.pixmap().width()

    page.resize(1200, 900)
    qapp.processEvents()

    large_width = page.image_label.pixmap().width()

    assert large_width > small_width


def test_inspection_page_clear_image_stops_rescaling(qapp):

    from modules.ui.inspection.inspection_page import InspectionPage

    page = InspectionPage()
    page.show()

    page.set_image(_frame())
    page.clear_image()

    page.resize(800, 600)
    qapp.processEvents()

    assert page.image_label.pixmap().isNull()
