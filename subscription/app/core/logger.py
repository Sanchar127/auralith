from __future__ import annotations

import logging
import sys


LOG_FORMAT = (
    "%(asctime)s | "
    "%(levelname)-8s | "
    "%(name)s | "
    "%(message)s"
)


def setup_logger() -> logging.Logger:
    """
    Configure application logging.
    """

    logger = logging.getLogger("subscription")

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)

    handler.setFormatter(
        logging.Formatter(LOG_FORMAT)
    )

    logger.addHandler(handler)

    logger.propagate = False

    return logger


logger = setup_logger()