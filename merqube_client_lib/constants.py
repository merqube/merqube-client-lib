"""
Merqube API constants
"""
from typing import Final

API_URL: Final[str] = "https://api.merqube.com"
STAGING_API_URL: Final[str] = "https://staging.api.merqube.com"
REQUEST_ID_HEADER: Final[str] = "X-Request-ID"

MERQ_REQUEST_ID_ENV_VAR: Final[str] = "MERQ_REQUEST_ID"
MERQ_REQUEST_REMOTE_ADDR_ENV_VAR: Final[str] = "MERQ_REQUEST_REMOTE_ADDR"
MERQ_RUN_ID_ENV_VAR: Final[str] = "MERQ-RUN-ID"

DEFAULT_CACHE_TTL: Final[int] = 600

MERQ_CLIENT_PREFIX = "mqu_py_client"

PRICE_RETURN: Final[str] = "price_return"
TOTAL_RETURN: Final[str] = "total_return"

INDEX_RUN_STATUS_METRIC: Final[str] = "index_run_status"
