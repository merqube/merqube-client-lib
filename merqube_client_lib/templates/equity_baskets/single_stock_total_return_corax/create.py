"""
Create an equity basket index
"""

import logging

from merqube_client_lib.logging import get_module_logger
from merqube_client_lib.pydantic_types import IdentifierUUIDPost, IndexDefinitionPost
from merqube_client_lib.templates.equity_baskets.util import (
    create_index,
    load_template,
    read_file,
)

logger = get_module_logger(__name__, level=logging.DEBUG)

TYPE_SPECIFIC_REQUIRED = ["underlying_ric"]

# Optional keys that have defaults
TYPE_SPECIFIC_OPTIONAL = ["level_overrides_csv_path"]


def create(config_file_path: str, prod_run: bool = False) -> tuple[IndexDefinitionPost, IdentifierUUIDPost | None]:
    """
    Creates a new Equity Basket with multiple entries
    This class does not handle Corax.
    """
    client, template, index_info, inner_spec = load_template(
        template_name="SINGLE_STOCK_TR_TEMPLATE_VERSION_1",
        config_file_path=config_file_path,
        type_specific_req_fields=TYPE_SPECIFIC_REQUIRED,
    )

    inner_spec["portfolios"]["constituents"] = [
        {
            "date": index_info["base_date"],
            "identifier": index_info["underlying_ric"],
            "quantity": 1,
        }
    ]

    inner_spec["currency"] = index_info.get("currency", "USD")

    if pth := index_info.get("level_overrides_csv_path"):
        inner_spec["level_overrides"] = read_file(pth)

    return create_index(
        client=client, template=template, index_info=index_info, inner_spec=inner_spec, prod_run=prod_run
    )
