"""Logging utility functions."""

import logging


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the given name."""
    return logging.getLogger(name)


def log_debug(logger: logging.Logger, message: str):
    """Log a debug message."""
    logger.debug(message)


def log_warning(logger: logging.Logger, message: str):
    """Log a warning message."""
    logger.warning(message)


def log_error(logger: logging.Logger, message: str):
    """Log an error message."""
    logger.error(message)


def log_info(logger: logging.Logger, message: str):
    """Log an info message."""
    logger.info(message)
