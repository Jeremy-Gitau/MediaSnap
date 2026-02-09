"""Logging configuration for MediaSnap."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from mediasnap.utils.config import LOG_FILE, APP_NAME


def setup_logging(level: int = logging.INFO, log_file: Optional[Path] = None) -> logging.Logger:
    """
    Configure and return the application logger.
    
    Args:
        level: Logging level (default: INFO)
        log_file: Path to log file (default: from config)
    
    Returns:
        Configured logger instance
    """
    if log_file is None:
        log_file = LOG_FILE
    
    # Create logger
    logger = logging.getLogger(APP_NAME)
    logger.setLevel(level)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    console_formatter = logging.Formatter(
        fmt="%(levelname)-8s | %(message)s"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (default: APP_NAME)
    
    Returns:
        Logger instance
    """
    if name is None:
        name = APP_NAME
    return logging.getLogger(name)
