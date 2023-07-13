"""
Merqube custom exceptions
"""

from typing import Any


class APIError(Exception):
    """Generic exception for when our client library hits a non 2xx code from our APIs"""

    def __init__(
        self, code: int | None = None, response_json: dict[str, Any] | None = None, request_id: str | None = None
    ):
        super().__init__()
        self.code = code
        self.response_json = response_json
        self.request_id = request_id


class PermissionsError(Exception):
    """Exception for when the user does not have the required permissions to perform an action"""


class IndexNotFound(Exception):
    """Exception for when an index is not found"""
