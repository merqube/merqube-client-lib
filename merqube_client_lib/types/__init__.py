"""
Merqube custom types
"""
from enum import Enum, unique
from typing import Final

HTTP_METHODS: Final[list[str]] = ["GET", "DELETE", "POST", "GET", "PUT", "OPTIONS", "PATCH"]


@unique
class HTTPMethod(str, Enum):
    GET = "GET"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    OPTIONS = "OPTIONS"
    POST = "POST"
    HEAD = "HEAD"
