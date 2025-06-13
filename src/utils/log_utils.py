"""
Logging utilities for Storyteller Box.
Configures structured logging with rotation.
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FILE = Path(__file__).parent.parent / "storyteller.log"

# Configure root logger
logger = logging.getLogger("storyteller")
logger.setLevel(logging.DEBUG)

# Rotating file handler: 1MB per file, keep 5 backups
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=5)
file_handler.setLevel(logging.DEBUG)
file_fmt = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
file_handler.setFormatter(file_fmt)

# Console handler (optional, for debugging)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_fmt = logging.Formatter('%(levelname)s: %(message)s')
console_handler.setFormatter(console_fmt)

# Add handlers if not already present
if not logger.hasHandlers():
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

# Usage: from utils.log_utils import logger
