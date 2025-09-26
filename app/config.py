"""
Configuration module for fussball.de scraping.

Defines constants for base URLs, HTTP timeouts, sleep intervals,
caching options, and user agent strings.
"""

import os

# Base URL for fussball.de
BASE: str = os.getenv("FBDE_BASE", "https://www.fussball.de")

# HTTP & scraping configs
REQUEST_TIMEOUT: float = float(os.getenv("REQUEST_TIMEOUT", "20"))
SLEEP_SEC: float = float(os.getenv("SLEEP_SEC", "0.4"))
ENRICH_SLEEP_SEC: float = float(os.getenv("ENRICH_SLEEP_SEC", "0.25"))

# Caching
CACHE_DIR: str = os.getenv("CACHE_DIR", ".cache_fussballde")
USE_CACHE_DEFAULT: bool = os.getenv("USE_CACHE", "1") == "1"

# UA
USER_AGENT: str = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
)
