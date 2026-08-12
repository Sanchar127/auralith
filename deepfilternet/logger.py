
from __future__ import annotations

import logging
import sys
from pathlib import Path


# =========================================================
# Configuration
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "deepfilternet.log"


LOG_FORMAT = (
    "%(asctime)s | "
    "%(levelname)s | "
    "%(name)s | "
    "%(message)s"
)


# =========================================================
# Logger
# =========================================================

logger = logging.getLogger("deepfilternet")

logger.setLevel(logging.INFO)

logger.propagate = False


# =========================================================
# Avoid duplicate handlers
# =========================================================

if not logger.handlers:

    # -----------------------------------------------------
    # Console handler
    # -----------------------------------------------------

    console_handler = logging.StreamHandler(
        sys.stdout
    )

    console_handler.setLevel(logging.INFO)

    console_handler.setFormatter(
        logging.Formatter(LOG_FORMAT)
    )

    # -----------------------------------------------------
    # File handler
    # -----------------------------------------------------

    file_handler = logging.FileHandler(
        LOG_FILE,
        encoding="utf-8",
    )

    file_handler.setLevel(logging.INFO)

    file_handler.setFormatter(
        logging.Formatter(LOG_FORMAT)
    )

    # -----------------------------------------------------
    # Register handlers
    # -----------------------------------------------------

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


logger.info(
    "DeepFilterNet logger initialized "
    "log_file=%s",
    LOG_FILE,
)

