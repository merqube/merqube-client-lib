from __future__ import annotations

import json
from typing import Any, cast

import pytz
from pydantic import Extra, validator
from pydantic.types import T

from merqube_client_lib.pydantic_types import (
    ClientDecrementConfig as _ClientDecrementConfig,
)
from merqube_client_lib.pydantic_types import (
    ClientIndexConfigBase as _ClientIndexConfigBase,
)
from merqube_client_lib.pydantic_types import (
    ClientMultiEBConfig as _ClientMultiEBConfig,
)
from merqube_client_lib.pydantic_types import ClientSSTRConfig as _ClientSSTRConfig

"""
************
TODO: 
delete this entire module.  This will go away once we move the generation server side. 
************
"""


class ClientIndexConfigBaseValidator(_ClientIndexConfigBase):
    class Config:
        extra = Extra.forbid

    @classmethod
    def get_example(cls) -> dict[str, Any]:
        """
                Construct an example from the class schema
                adapted from https://github.com/pydantic/pydantic/discussions/4558
        __holiday_spec__"""
        d = {}
        for field_name, model_field in cls.__fields__.items():
            if "example" in model_field.field_info.extra:
                d[field_name] = model_field.field_info.extra["example"]

        instance = cls(**d)
        return cast(dict[str, Any], json.loads(instance.json()))

    @validator("timezone")
    def is_valid_tz(cls: T, v: str) -> str:  # pylint: disable=no-self-argument
        if v not in pytz.all_timezones:
            raise ValueError(f"Invalid timezone string: {v}")
        return v

    @validator("run_hour")
    def is_valid_hour(cls: T, v: int) -> int:  # pylint: disable=no-self-argument
        if v < 0 or v > 23:
            raise ValueError(f"Invalid timezone string: {v}")
        return v

    @validator("run_minute")
    def is_valid_minute(cls: T, v: int) -> int:  # pylint: disable=no-self-argument
        if v < 0 or v > 59:
            raise ValueError(f"Invalid timezone string: {v}")
        return v


class ClientSSTRConfig(ClientIndexConfigBaseValidator, _ClientSSTRConfig):
    """
    Single stock total return index
    """

    class Config:
        extra = Extra.forbid


class ClientDecrementConfig(ClientIndexConfigBaseValidator, _ClientDecrementConfig):
    """
    Decrement index on top of an SSTR
    Calendar automatically set to that of the underlying
    """

    class Config:
        extra = Extra.forbid


class ClientMultiEquityBasketConfig(ClientIndexConfigBaseValidator, _ClientMultiEBConfig):
    """
    Equity Basket
    """

    class Config:
        extra = Extra.forbid
