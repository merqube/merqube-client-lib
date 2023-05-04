"""
Merqube API constants
"""
from typing import Final

API_URL: Final[str] = "https://api.merqube.com"
REQUEST_ID_HEADER: Final[str] = "X-Request-ID"

MERQ_REQUEST_ID_ENV_VAR: Final[str] = "MERQ_REQUEST_ID"
MERQ_REQUEST_REMOTE_ADDR_ENV_VAR: Final[str] = "MERQ_REQUEST_REMOTE_ADDR"
MERQ_RUN_ID_ENV_VAR: Final[str] = "MERQ-RUN-ID"

DEFAULT_CACHE_TTL: Final[int] = 600
