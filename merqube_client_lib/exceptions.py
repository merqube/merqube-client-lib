"""
Merqube custom exceptions
"""

from typing import Any

PERMISSION_ERROR_RES = {"code": "00001", "message": "RESULTS_WERE_FILTERED"}


class IndexNotFound(Exception):
    """Exception for when an index is not found"""


class APIError(Exception):
    """Generic exception for when our client library hits a non 2xx code from our APIs"""

    def __init__(
        self, code: int | None = None, response_json: dict[str, Any] | None = None, request_id: str | None = None
    ):
        super().__init__()
        self.code = code
        self.response_json = response_json
        self.request_id = request_id
