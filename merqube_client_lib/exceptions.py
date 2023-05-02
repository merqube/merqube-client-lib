"""
Merqube custom exceptions
"""

from typing import Any


class APIError(Exception):
    """Generic exception for when our client library hits a non 2xx code from our APIs"""

    def __init__(self, code: int | None = None, response_json: dict[str, Any] | None = None):
        super().__init__()
        self.code = code
        self.response_json = response_json

    def __str__(self) -> str:
        return f"API Error: code: {self.code}, response_json: {self.response_json}"
