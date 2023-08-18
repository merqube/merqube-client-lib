from __future__ import annotations

import json
from typing import Any, cast

from pydantic import Extra, Field

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
        return cast(dict[str, Any], dict(sorted(json.loads(instance.json()).items(), key=lambda x: x[0])))  # type: ignore


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


class ClientMultiEquityBasketConfig(ClientIndexConfigBaseValidator, _ClientMultiEBConfig):  # type: ignore
    """
    Equity Basket
    """

    class Config:
        extra = Extra.forbid

    constituents_csv_path: str = Field(..., description="path to constituents csv", example="/path/to/constituents.csv")
    level_overrides_csv_path: str | None = Field(
        None,
        description="optional and only needed if you need to provide specific overrides for your index on given days",
        example="/path/to/overrides.csv",
    )


# these are "_csv_path" in the client model, but the client transforms these into the server model _ClientMultiEBConfig
# https://github.com/pydantic/pydantic/discussions/2686#discussioncomment-6607215
del ClientMultiEquityBasketConfig.__fields__["constituents"]
del ClientMultiEquityBasketConfig.__fields__["level_overrides"]
