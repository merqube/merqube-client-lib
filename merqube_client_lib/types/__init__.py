"""
Merqube custom types
"""
from dataclasses import dataclass
from enum import Enum, unique
from typing import Any, Final

import pandas as pd

from merqube_client_lib.pydantic_types import (
    EquityBasketPortfolio,
    IdentifierUUIDPost,
    IndexDefinitionPost,
)

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


Manifest = dict[str, Any]
ManifestList = list[Manifest]

Records = list[dict[str, str]]

TargetPortfoliosDates = list[tuple[pd.Timestamp, EquityBasketPortfolio]]

ResponseJson = dict[str, Any]


@dataclass
class CreateReturn:
    template: IndexDefinitionPost
    ident: IdentifierUUIDPost | None = None
    initial_target_ports: TargetPortfoliosDates | None = None
