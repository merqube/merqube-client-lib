from __future__ import annotations

import json
import logging
from typing import Any, cast

from pydantic import Extra, Field

from merqube_client_lib.logging import get_module_logger
from merqube_client_lib.pydantic_v2_types import (
    ClientBufferConfig as _ClientBufferConfig,
)
from merqube_client_lib.pydantic_v2_types import (
    ClientDecrementConfig as _ClientDecrementConfig,
)
from merqube_client_lib.pydantic_v2_types import (
    ClientIndexConfigBase as _ClientIndexConfigBase,
)
from merqube_client_lib.pydantic_v2_types import (
    ClientMultiEBConfig as _ClientMultiEBConfig,
)
from merqube_client_lib.pydantic_v2_types import ClientSSTRConfig as _ClientSSTRConfig

logger = get_module_logger(__name__, level=logging.DEBUG)


class ClientIndexConfigBaseValidator(_ClientIndexConfigBase):
    class Config:
        extra = Extra.forbid

    @classmethod
    def get_example(cls) -> dict[str, Any]:
        """
        Construct an example from the class schema
        adapted from https://github.com/pydantic/pydantic/discussions/4558
        """
        d = {}
        for field_name, model_field in cls.__fields__.items():  # type: ignore
            logger.info((field_name, model_field))
            if (
                (jse := getattr(model_field, "json_schema_extra", {}))
                and (ex := jse.get("example"))
                and field_name not in ["constituents", "level_overrides"]
            ):
                d[field_name] = ex

        instance = cls(**d)

        example_d = cast(dict[str, Any], dict(sorted(json.loads(instance.json()).items(), key=lambda x: x[0])))  # type: ignore

        # these fields are injected based on the csv path(s), so for the purposes of fetching
        # an example, they should not be shown to the user
        for k in ["constituents", "level_overrides"]:
            if k in d:
                example_d[k] = d[k]

        return example_d


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

    constituents_csv_path: str = Field(..., description="path to constituents csv", example="/path/to/constituents.csv")
    level_overrides_csv_path: str | None = Field(
        None,
        description="optional and only needed if you need to provide specific overrides for your index on given days",
        example="/path/to/overrides.csv",
    )


class ClientBufferSimpleConfig(ClientIndexConfigBaseValidator, _ClientBufferConfig):
    """
    Simple buffer index
    """

    class Config:
        extra = Extra.forbid
