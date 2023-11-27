"""This file contains the logic for setting up logging."""
import sys
from logging import (
    DEBUG,
    INFO,
    FileHandler,
    Formatter,
    Handler,
    Logger,
    StreamHandler,
    getLogger,
)


def setup_loggers() -> None:
    """Sets up the printer and debug loggers."""
    printer_handler = StreamHandler(sys.stdout)
    create_logger(
        "printer",
        INFO,
        printer_handler,
        "%(asctime)s: %(message)s",
        "%H:%M:%S",
    )

    debug_handler = FileHandler("log.log", encoding="utf-8")
    debug = create_logger(
        "debug",
        DEBUG,
        debug_handler,
        "%(asctime)s %(levelname)s from %(filename)s %(funcName)s in %(threadName)s - %(message)s",
    )

    debug.debug("Loggers configured")


def create_logger(
    name: str,
    level: int,
    output_handler: Handler,
    format_str: str,
    date_format: str | None = None,
) -> Logger:
    """Creates a logger with the given options.

    Args:
        name: The name of the logger.
        level: The logging level.
        output_handler: The handler for the logger to use.
        format_str: The format string to use.
        date_format: The format to use for dates.

    Returns:
        The created logger.

    """
    logger = getLogger(name)
    logger.setLevel(level)

    formatter = Formatter(format_str, date_format)
    output_handler.setFormatter(formatter)

    logger.addHandler(output_handler)

    return logger
