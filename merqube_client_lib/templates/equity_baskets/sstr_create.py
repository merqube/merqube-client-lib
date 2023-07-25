"""
Create an equity basket index
"""
import logging
from typing import Any, cast

from merqube_client_lib.logging import get_module_logger
from merqube_client_lib.templates.equity_baskets.schema import ClientSSTRConfig
from merqube_client_lib.templates.equity_baskets.util import create_index, load_template
from merqube_client_lib.types import CreateReturn

logger = get_module_logger(__name__, level=logging.DEBUG)


def create(config: dict[str, Any], prod_run: bool = False, poll: int = 0) -> CreateReturn:
    """
    Creates a new Equity Basket with multiple entries
    This class does not handle Corax.
    """
    client, template, index_info, inner_spec = load_template(
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

    inner_spec["currency"] = index_info.currency

    post_template, ident_ppost = create_index(
        client=client, template=template, index_info=index_info, inner_spec=inner_spec, prod_run=prod_run, poll=poll
    )

    return CreateReturn(post_template, ident_ppost)
