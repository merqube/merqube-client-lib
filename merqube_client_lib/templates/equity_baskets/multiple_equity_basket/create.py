"""
Create an equity basket index
"""

from merqube_client_lib.logging import get_module_logger
from merqube_client_lib.templates.equity_baskets.multiple_equity_basket.base import (
    TYPE_SPECIFIC_OPTIONAL,
    TYPE_SPECIFIC_REQUIRED,
    get_constituents,
    inline_to_tp,
)
from merqube_client_lib.templates.equity_baskets.util import (
    create_index,
    load_template,
    read_file,
)
from merqube_client_lib.types import CreateReturn

logger = get_module_logger(__name__)


def create(config_file_path: str, prod_run: bool = False) -> CreateReturn:
    """
    Creates a new Equity Basket with multiple entries
    This class does not handle Corax.
    """
    client, template, index_info, inner_spec = load_template(
        template_name="EQUITY_BASKET_TEMPLATE_V1",
        config_file_path=config_file_path,
        type_specific_req_fields=TYPE_SPECIFIC_REQUIRED,
        type_specific_opt_fields=TYPE_SPECIFIC_OPTIONAL,
    )

    const = get_constituents(
        constituents_csv_path=index_info["constituents_csv_path"],
        base_date=index_info["base_date"],
        base_value=index_info["base_value"],
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

    if pth := index_info.get("level_overrides_csv_path"):
        inner_spec["level_overrides"] = read_file(pth)

    post_template, ident = create_index(
        client=client,
        template=template,
        index_info=index_info,
        inner_spec=inner_spec,
        prod_run=prod_run,
        initial_target_portfolios=target_portfolios,
    )

    return CreateReturn(template=post_template, ident=ident, initial_target_ports=target_portfolios)
