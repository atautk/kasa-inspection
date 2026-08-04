import logging

import pytest

from modules.utils import logger as logger_module


def _clear_named_logger_handlers():

    # "kasa_inspection" adlı logger, Python'un logging modülünde
    # SÜREÇ genelinde tek bir nesne olarak önbelleklenir. Başka bir
    # modül (ör. band_manager.py) daha önce gerçek get_logger()'ı
    # tetiklediyse, bu logger'a zaten gerçek logs/app.log'a yazan bir
    # handler eklenmiş olabilir - modules.utils.logger._logger'ı
    # sıfırlamak tek başına bunu temizlemez, handler'ı da ayrıca
    # kaldırmak gerekir.

    logger = logging.getLogger("kasa_inspection")

    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)


@pytest.fixture(autouse=True)
def isolated_logger(tmp_path, monkeypatch):

    _clear_named_logger_handlers()

    monkeypatch.setattr(logger_module, "LOG_DIR", tmp_path)
    monkeypatch.setattr(logger_module, "LOG_FILE", tmp_path / "app.log")
    monkeypatch.setattr(logger_module, "_logger", None)

    yield

    # Sonraki testlerin (ve diğer test dosyalarının) etkilenmemesi
    # için logger'ı ve handler'larını tamamen temizle
    # (RotatingFileHandler dosyayı açık tutuyor).
    _clear_named_logger_handlers()

    logger_module._logger = None

    logger_module._logger = None


def test_creates_log_dir_and_file(tmp_path):

    logger = logger_module.get_logger()
    logger.info("test mesajı")

    for handler in logger.handlers:
        handler.flush()

    assert logger_module.LOG_FILE.exists()
    assert "test mesajı" in logger_module.LOG_FILE.read_text(encoding="utf-8")


def test_returns_same_singleton_instance():

    first = logger_module.get_logger()
    second = logger_module.get_logger()

    assert first is second
    assert len(first.handlers) == 1


def test_uses_rotating_file_handler():

    logger = logger_module.get_logger()

    from logging.handlers import RotatingFileHandler

    assert isinstance(logger.handlers[0], RotatingFileHandler)
    assert logger.handlers[0].maxBytes == logger_module.MAX_BYTES
    assert logger.handlers[0].backupCount == logger_module.BACKUP_COUNT


def test_log_file_rotates_when_size_limit_exceeded(tmp_path, monkeypatch):

    monkeypatch.setattr(logger_module, "MAX_BYTES", 500)

    logger = logger_module.get_logger()

    for i in range(200):
        logger.info("dolgu satırı %d - biraz uzun bir mesaj olsun", i)

    for handler in logger.handlers:
        handler.flush()

    rotated = tmp_path / "app.log.1"

    assert rotated.exists()
    assert logger_module.LOG_FILE.exists()
