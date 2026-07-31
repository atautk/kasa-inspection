import logging
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_FILE = LOG_DIR / "app.log"

_logger = None


def get_logger() -> logging.Logger:
    """
    Uygulama genelinde kullanılan tek logger.

    Beklenmeyen hatalar (kamera kopması, işlenmemiş exception'lar)
    konsola değil logs/app.log dosyasına yazılır — fabrikada kimse
    konsolu izlemediği için bu, sorun sonradan anlaşılabilsin diye
    gerekli.
    """

    global _logger

    if _logger is not None:
        return _logger

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("kasa_inspection")
    logger.setLevel(logging.INFO)

    if not logger.handlers:

        handler = logging.FileHandler(LOG_FILE, encoding="utf-8")

        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s"
            )
        )

        logger.addHandler(handler)

    _logger = logger

    return logger
