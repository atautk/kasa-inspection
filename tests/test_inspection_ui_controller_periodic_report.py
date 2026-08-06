from datetime import datetime, timezone, timedelta

import pytest

from modules.configuration.band import Band
from modules.configuration.inspection_logger import InspectionLogger
from modules.configuration.telegram_settings import TelegramSettings
from modules.core.telegram_notifier import TelegramNotifier


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

    from modules.ui.inspection.inspection_window import InspectionWindow
    from modules.ui.inspection.inspection_ui_controller import (
        InspectionUIController
    )

    window = InspectionWindow()

    ctrl = InspectionUIController(window, root=tmp_path, operator_name="test")

    band = Band(
        id="band_01",
        name="Test Bandı",
        root=tmp_path / "band_01",
        reference=tmp_path / "band_01" / "reference.png",
        roi=tmp_path / "band_01" / "roi.json",
        models=tmp_path / "band_01" / "models"
    )
    band.root.mkdir(parents=True, exist_ok=True)

    ctrl.current_band = band
    ctrl.inspection_logger = InspectionLogger(band)

    yield ctrl

    # bkz. tests/conftest.py - açık bırakılan pencereler test paketi
    # boyunca Qt native kaynaklarının birikmesine yol açabiliyordu.
    window.close()


def _configured_settings(**overrides):

    settings = TelegramSettings(bot_token="tok", chat_id="chat")

    for key, value in overrides.items():
        setattr(settings, key, value)

    return settings


# -------------------------------------------------
# _resolve_report_period_start
# -------------------------------------------------

def test_resolve_period_start_never_sent_returns_24h_ago(controller):

    now = datetime(2026, 1, 2, tzinfo=timezone.utc)
    settings = _configured_settings(last_daily_report_sent_at="")

    since = controller._resolve_report_period_start(settings, now)

    assert since == now - timedelta(hours=24)


def test_resolve_period_start_within_window_returns_none(controller):

    now = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)
    last_sent = now - timedelta(hours=1)

    settings = _configured_settings(
        last_daily_report_sent_at=last_sent.isoformat()
    )

    assert controller._resolve_report_period_start(settings, now) is None


def test_resolve_period_start_after_window_returns_last_sent(controller):

    now = datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc)
    last_sent = now - timedelta(hours=25)

    settings = _configured_settings(
        last_daily_report_sent_at=last_sent.isoformat()
    )

    since = controller._resolve_report_period_start(settings, now)

    assert since == last_sent


def test_resolve_period_start_invalid_timestamp_falls_back(controller):

    now = datetime(2026, 1, 2, tzinfo=timezone.utc)

    settings = _configured_settings(
        last_daily_report_sent_at="not-a-valid-date"
    )

    since = controller._resolve_report_period_start(settings, now)

    assert since == now - timedelta(hours=24)


# -------------------------------------------------
# _maybe_send_periodic_report
# -------------------------------------------------

def test_maybe_send_report_skips_when_disabled(controller):

    controller.telegram_settings_manager.save(
        _configured_settings(daily_report_enabled=False)
    )

    controller._maybe_send_periodic_report()

    assert controller._telegram_report_thread is None


def test_maybe_send_report_skips_when_no_band(controller):

    controller.current_band = None

    controller.telegram_settings_manager.save(
        _configured_settings(daily_report_enabled=True)
    )

    controller._maybe_send_periodic_report()

    assert controller._telegram_report_thread is None


def test_maybe_send_report_generates_and_sends_document(
    controller, monkeypatch
):

    controller.telegram_settings_manager.save(
        _configured_settings(daily_report_enabled=True)
    )

    controller.inspection_logger.log(
        {"G01": {"state": "FULL", "expected": "FULL", "ok": True,
                 "change_ratio": 1.0, "changed_pixels": 1}},
        "clio"
    )

    sent_documents = []

    def fake_send_document(self, file_path, caption=""):
        sent_documents.append((file_path, caption))
        return 111

    monkeypatch.setattr(
        TelegramNotifier, "send_document", fake_send_document
    )

    controller._maybe_send_periodic_report()

    assert controller._telegram_report_thread is not None
    controller._telegram_report_thread.join(timeout=5)

    assert len(sent_documents) == 1

    report_path = sent_documents[0][0]
    assert report_path.endswith(".xlsx")
    from pathlib import Path
    assert Path(report_path).exists()

    updated = controller.telegram_settings_manager.load()
    assert updated.last_daily_report_sent_at != ""


def test_maybe_send_report_enqueues_on_failure(controller, monkeypatch):

    controller.telegram_settings_manager.save(
        _configured_settings(daily_report_enabled=True)
    )

    monkeypatch.setattr(
        TelegramNotifier, "send_document", lambda self, path, caption="": None
    )

    controller._maybe_send_periodic_report()
    controller._telegram_report_thread.join(timeout=5)

    queued = controller.telegram_queue.load()

    assert len(queued) == 1
    assert queued[0].kind == "document"
    assert queued[0].chat_id == "chat"


def test_maybe_send_report_throttles_repeated_calls(controller, monkeypatch):

    controller.telegram_settings_manager.save(
        _configured_settings(daily_report_enabled=True)
    )

    calls = []

    monkeypatch.setattr(
        TelegramNotifier,
        "send_document",
        lambda self, path, caption="": (calls.append(1), 1)[1]
    )

    controller._maybe_send_periodic_report()
    controller._telegram_report_thread.join(timeout=5)

    # Aynı kontrol penceresinde hemen tekrar çağrıldığında, ikinci
    # çağrı REPORT_CHECK_INTERVAL_SECONDS dolmadığı için hiçbir şey
    # yapmamalı (yeni bir thread başlatmamalı).
    thread_after_first = controller._telegram_report_thread

    controller._maybe_send_periodic_report()

    assert controller._telegram_report_thread is thread_after_first
    assert len(calls) == 1
