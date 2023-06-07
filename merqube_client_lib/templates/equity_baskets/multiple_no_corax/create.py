"""
Create an equity basket index
"""
from typing import Any, cast

import pandas as pd

from merqube_client_lib.logging import get_module_logger
from merqube_client_lib.pydantic_types import IdentifierUUIDPost, IndexDefinitionPost
from merqube_client_lib.templates.equity_baskets.util import (
    create_index,
    load_template,
    read_file,
)

logger = get_module_logger(__name__)

TYPE_SPECIFIC_REQUIRED = ["constituents_csv_path", "base_value"]

# Optional keys that have defaults
TYPE_SPECIFIC_OPTIONAL = ["level_overrides_csv_path"]


def _get_constituents(base_date: str | pd.Timestamp, base_value: float, constituents_csv_path: str) -> dict[str, Any]:
    """read and validate constituents file"""
    constituents = read_file(constituents_csv_path)

    if pd.Timestamp(base_date) >= pd.Timestamp(min(c["date"] for c in constituents)):
        raise ValueError("base_date should be set to a date at least one day before the first portfolio date")

    inline = cast(
        dict[str, Any],
        [
            {
                "date": base_date,
                "identifier": "USD",
                "quantity": base_value,
                "security_type": "CASH",
            }
        ]
        + constituents,
    )

    return inline


def create(config_file_path: str, prod_run: bool = False) -> tuple[IndexDefinitionPost, IdentifierUUIDPost | None]:
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

    ports = {
        "constituents": _get_constituents(
            constituents_csv_path=index_info["constituents_csv_path"],
            base_date=index_info["base_date"],
            base_value=index_info["base_value"],
        ),
        "date_type": "EFFECTIVE",
        "identifier_type": "RIC",
        "quantity_type": "SHARES",
        "specification_type": "INLINE",
    }

    inner_spec["portfolios"] = ports

    # TODO: do both and compare
    # TODO: on the target portfolio, set the specifcation type to API
    # target_portfolios = inline_to_tp(template)

    if pth := index_info.get("level_overrides_csv_path"):
        inner_spec["level_overrides"] = read_file(pth)

    return create_index(
        client=client, template=template, index_info=index_info, inner_spec=inner_spec, prod_run=prod_run
    )
