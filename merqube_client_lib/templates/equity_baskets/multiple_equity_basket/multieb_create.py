"""
Create an equity basket index
"""
from typing import Any, cast

import pandas as pd

from merqube_client_lib.logging import get_module_logger
from merqube_client_lib.templates.equity_baskets.multiple_equity_basket.base import (
    get_constituents,
    inline_to_tp,
)
from merqube_client_lib.templates.equity_baskets.schema import (
    ClientMultiEquityBasketConfig,
)
from merqube_client_lib.templates.equity_baskets.util import (
    create_index,
    load_template,
    read_file,
)
from merqube_client_lib.types import CreateReturn

logger = get_module_logger(__name__)


def create(config: dict[str, Any], prod_run: bool = False, poll: int = 0) -> CreateReturn:
    """
    Creates a new Equity Basket with multiple entries
    """
    client, template, index_info, inner_spec = load_template(
        template_name="EQUITY_BASKET_TEMPLATE_V1",
        config=config,
        model=ClientMultiEquityBasketConfig,
    )

    index_info = cast(ClientMultiEquityBasketConfig, index_info)

    if index_info.corporate_actions.reinvest_dividends:
        # unfortunately, this class has all corax on except for dividend reinvestment -
        # the standard case for this client tool is to turn dividend reinvestment on;
        # we cannot just delete the whole corporate_actions dict
        inner_spec["corporate_actions"] = {
            "dividend": {"deduct_tax": False, "reinvest_day": "PREV_DAY", "reinvest_strategy": "IN_INDEX"}
        }

    const = get_constituents(
        constituents_csv_path=index_info.constituents_csv_path,
        base_date=cast(pd.Timestamp, index_info.base_date),
        base_value=index_info.base_value,
        add_initial_cash_position=True,
    )

    ports = {
        "constituents": const,
        "date_type": "EFFECTIVE",
        "identifier_type": "RIC",
        "quantity_type": "SHARES",
        "specification_type": "API",
    }

    target_portfolios = inline_to_tp(ports)

    inner_spec["portfolios"]["specification_type"] = "API"
    inner_spec["portfolios"]["constituents"] = []

    if pth := index_info.level_overrides_csv_path:
        inner_spec["level_overrides"] = read_file(pth)

    post_template, ident = create_index(
        client=client,
        template=template,
        index_info=index_info,
        inner_spec=inner_spec,
        prod_run=prod_run,
        initial_target_portfolios=target_portfolios,
        poll=poll,
    )

    return CreateReturn(template=post_template, ident=ident, initial_target_ports=target_portfolios)
