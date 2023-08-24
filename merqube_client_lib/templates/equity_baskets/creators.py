"""
equity basket creators
"""
import logging
from typing import Any

import pandas as pd

from merqube_client_lib.logging import get_module_logger
from merqube_client_lib.pydantic_v2_types import (
    ClientMultiEBConfig,
    ClientTemplateResponse,
)
from merqube_client_lib.templates.equity_baskets.schema import (
    ClientDecrementConfig,
    ClientMultiEquityBasketConfig,
    ClientSSTRConfig,
)
from merqube_client_lib.templates.equity_baskets.util import EquityBasketIndexCreator

logger = get_module_logger(__name__, level=logging.DEBUG)


def read_file(filename: str) -> list[Any]:
    """reads portfolio/overrides files"""
    return list(pd.read_csv(filename, float_precision="round_trip").to_dict(orient="index").values())


class SSTRIndexCreator(EquityBasketIndexCreator):
    """create a SSTR index"""

    def __init__(self) -> None:
        super().__init__(itype="sstr", model=ClientSSTRConfig)

    def create(self, config: dict[str, Any], prod_run: bool, poll: int) -> ClientTemplateResponse:
        return self._create(config=config, prod_run=prod_run, poll=poll)


class DecrementIndexCreator(EquityBasketIndexCreator):
    """create a decrement index on top of a SSTR"""

    def __init__(self) -> None:
        super().__init__(itype="sstr_decrement", model=ClientDecrementConfig)

    def create(self, config: dict[str, Any], prod_run: bool, poll: int) -> ClientTemplateResponse:
        return self._create(config=config, prod_run=prod_run, poll=poll)


class MultiEBIndexCreator(EquityBasketIndexCreator):
    """create a generic equity basket"""

    def __init__(self) -> None:
        super().__init__(itype="multi_eb", model=ClientMultiEBConfig)

    def create(self, config: dict[str, Any], prod_run: bool, poll: int) -> ClientTemplateResponse:
        # this isnt in the server generated pydantic model since this is transformed into the proper constituents. this is only client side:
        ClientMultiEquityBasketConfig(**config)
        assert config.get("constituents_csv_path"), "constituents_csv_path must be provided"
        config["constituents"] = read_file(config["constituents_csv_path"])
        del config["constituents_csv_path"]
        if pth := config.get("level_overrides_csv_path"):
            config["level_overrides"] = read_file(pth)
            del config["level_overrides_csv_path"]
        return self._create(config=config, prod_run=prod_run, poll=poll)
