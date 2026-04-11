import logging
from typing import Optional


LOGGER_NAME = "seqtypo"
_logger = logging.getLogger(LOGGER_NAME)
_logger.addHandler(logging.NullHandler())


def get_logger() -> logging.Logger:
    """Return the package logger used by seqtypo services and models."""
    return _logger


def set_logger(logger: logging.Logger) -> None:
    """Replace the package logger with a custom logger provided by consumers."""
    global _logger
    _logger = logger


def configure_logger(
    *,
    level: int = logging.INFO,
    handler: Optional[logging.Handler] = None,
    propagate: bool = False,
) -> logging.Logger:
    """
    Configure and return the package logger.

    Applications can call this helper to route seqtypo logs to their own handlers.
    """
    logger = get_logger()
    logger.setLevel(level)
    logger.propagate = propagate
    if handler is not None:
        logger.handlers = [handler]
    elif not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger
