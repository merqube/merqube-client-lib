"""
Create an equity basket index
"""
import logging
import os
from typing import Final

import click

from merqube_client_lib.logging import get_module_logger
from merqube_client_lib.templates.equity_baskets.decrement.create import (
    create as dec_index,
)
from merqube_client_lib.templates.equity_baskets.multiple_no_corax.create import (
    create as mult_index,
)
from merqube_client_lib.templates.equity_baskets.single_stock_total_return_corax.create import (
    create as ss_index,
)

SUPPORTED_INDEX_TYPES: Final[list[str]] = ["decrement", "single_stock_total_return", "multi_basket_no_corax"]

logger = get_module_logger(__name__, level=logging.DEBUG)


@click.command()
@click.option(
    "--index-type",
    type=click.Choice(SUPPORTED_INDEX_TYPES),
    required=True,
    help=f"type of index to create; must be one of {SUPPORTED_INDEX_TYPES}",
)
@click.option(
    "--config-file-path", type=str, required=True, help="path to the config file that follows the index template"
)
@click.option("--prod-run", is_flag=True, default=False, help="Create the index in production")
def main(index_type: str, config_file_path: str, prod_run: bool) -> None:
    """main entrypoint"""
    assert os.path.exists(config_file_path), f"Config file path does not exist: {config_file_path}"
    match index_type:
        case "decrement":
            func = dec_index
        case "single_stock_total_return":
            func = ss_index
        case "multi_basket_no_corax":
            func = mult_index
        case _:
            raise ValueError(f"Unknown index type: {index_type}")

    func(config_file_path=config_file_path, prod_run=prod_run)


if __name__ == "__main__":
    main()  # pyright: ignore  # pylint: disable=no-value-for-parameter
