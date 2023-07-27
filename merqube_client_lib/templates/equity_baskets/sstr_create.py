"""
Create an equity basket index
"""
import logging
from typing import Any, cast

from merqube_client_lib.constants import PRICE_RETURN
from merqube_client_lib.logging import get_module_logger
from merqube_client_lib.templates.equity_baskets.schema import (
    ClientSSTRConfig,
    reinvestment_mapping,
)
from merqube_client_lib.templates.equity_baskets.util import EquityBasketIndexCreator
from merqube_client_lib.types import CreateReturn

logger = get_module_logger(__name__, level=logging.DEBUG)


class SSTRCreator(EquityBasketIndexCreator):
    """create a single stock total return index"""

    @property
    def output_metric(self) -> str:
        return PRICE_RETURN

    def create(self, config: dict[str, Any], prod_run: bool = False, poll: int = 0) -> CreateReturn:
        """
        Creates a new Equity Basket with multiple entries
        This class does not handle Corax.
        """
        client, template, index_info, inner_spec = self._load_template(
            template_name="SINGLE_STOCK_TR_TEMPLATE_VERSION_1", config=config, model=ClientSSTRConfig
        )

        index_info = cast(ClientSSTRConfig, index_info)

        inner_spec["portfolios"]["constituents"] = [
            {
                "date": index_info.base_date,
                "identifier": index_info.ric,
                "quantity": 1,
            }
        ]

        inner_spec["corporate_actions"]["dividend"]["reinvest_day"] = reinvestment_mapping[index_info.reinvestment_type]

        inner_spec["currency"] = index_info.currency

        post_template, ident_ppost = self._create_index(
            client=client, template=template, index_info=index_info, inner_spec=inner_spec, prod_run=prod_run, poll=poll
        )

        return CreateReturn(post_template, ident_ppost)
