from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from app.config import LOG_FILE_PATH

_LOGGERS: dict[str, logging.Logger] = {}
_CONSOLE_ENABLED = False
_CONSOLE_LEVEL = logging.INFO


def _build_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        LOG_FILE_PATH,
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(file_handler)

    _maybe_attach_console(logger)

    return logger


def _maybe_attach_console(logger: logging.Logger) -> None:
    if not _CONSOLE_ENABLED:
        return
    console_handler = logging.StreamHandler()
    console_handler.name = "console"
    console_handler.setLevel(_CONSOLE_LEVEL)
    console_handler.setFormatter(
        logging.Formatter("%(levelname)s: %(message)s")
    )
    logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    if name not in _LOGGERS:
        _LOGGERS[name] = _build_logger(name)
    return _LOGGERS[name]


def configure_console(verbose: bool = False) -> None:
    global _CONSOLE_ENABLED, _CONSOLE_LEVEL
    _CONSOLE_ENABLED = True
    _CONSOLE_LEVEL = logging.DEBUG if verbose else logging.WARNING
    for logger in _LOGGERS.values():

        logger.handlers = [h for h in logger.handlers if h.name != "console"]
        _maybe_attach_console(logger)
