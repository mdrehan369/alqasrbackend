import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | "
    "%(name)s | %(filename)s:%(lineno)d | %(message)s"
)

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def setup_logger(name: str = "fastapi"):
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    formatter = logging.Formatter(
        LOG_FORMAT,
        datefmt=DATE_FORMAT
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    # Application log handler
    app_handler = RotatingFileHandler(
        f"{LOG_DIR}/app.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5
    )
    app_handler.setLevel(logging.DEBUG)
    app_handler.setFormatter(formatter)

    # Error-only handler
    error_handler = RotatingFileHandler(
        f"{LOG_DIR}/error.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(app_handler)
    logger.addHandler(error_handler)

    return logger


logger = setup_logger()
