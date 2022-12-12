"""This file contains the logic for setting up logging."""
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
from sys import stdout


def create_logger(
    name: str,
    level: int,
    handler: Handler,
    format_str: str,
) -> Logger:
    """Creates a logger with the given options.

    Args:
        name: The name of the logger.
        level: The logging level.
        handler: The handler for the logger to use.
        format_str: The format string to use.

    Returns:
        The created logger.

    """
    logger = getLogger(name)
    logger.setLevel(level)

    formatter = Formatter(format_str)
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    return logger


def setup_loggers() -> None:
    """Sets up the printer and debug loggers."""
    printer_handler = StreamHandler(stdout)
    create_logger('printer', INFO, printer_handler, '%(asctime)s: %(message)s')

    debug_handler = FileHandler('log.log')
    debug = create_logger(
        'debug',
        DEBUG,
        debug_handler,
        '%(asctime)s %(levelname)s from %(filename)s %(funcName)s in %(processName)s - %(message)s',
    )

    debug.debug('Loggers configured')
