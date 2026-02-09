"""Configuration management for MediaSnap."""

import os
from pathlib import Path
from typing import List

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Database configuration
DB_PATH = PROJECT_ROOT / "mediasnap.db"
DB_URL = f"sqlite:///{DB_PATH}"

# Download configuration
DOWNLOAD_DIR = PROJECT_ROOT / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Logs configuration
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "mediasnap.log"

# Rate limiting configuration
REQUEST_DELAY = 3.0  # Seconds between requests
REQUEST_JITTER = 0.6  # ±20% randomization (0.6 = 20% of 3.0)
MAX_CONCURRENT_DOWNLOADS = 3

# Retry configuration
MAX_RETRIES = 3
RETRY_INITIAL_WAIT = 2.0  # Seconds
RETRY_MAX_WAIT = 30.0  # Seconds
RETRY_MULTIPLIER = 2.0  # Exponential backoff

# HTTP configuration
CONNECT_TIMEOUT = 30.0  # Seconds
READ_TIMEOUT = 300.0  # Seconds
DOWNLOAD_CHUNK_SIZE = 8192  # Bytes

# User agent pool for rotation
USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]

# Instagram endpoints
INSTAGRAM_BASE_URL = "https://www.instagram.com"
INSTAGRAM_GRAPHQL_URL = f"{INSTAGRAM_BASE_URL}/graphql/query/"

# App information
APP_NAME = "MediaSnap"
APP_VERSION = "0.1.0"
