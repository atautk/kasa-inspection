import logging
from logging.handlers import RotatingFileHandler

from modules.utils.paths import get_app_root

LOG_DIR = get_app_root() / "logs"
LOG_FILE = LOG_DIR / "app.log"

# Fabrikada makine sürekli açık kalabildiği için app.log sınırsız
# büyümesin diye döndürülüyor: 5 MB'a ulaşınca app.log.1, app.log.2
# ... şeklinde en fazla 5 yedek dosya tutulur, eskiler silinir.
MAX_BYTES = 5_000_000
BACKUP_COUNT = 5

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

        handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8"
        )

        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s"
            )
        )

        logger.addHandler(handler)

    _logger = logger

    return logger
