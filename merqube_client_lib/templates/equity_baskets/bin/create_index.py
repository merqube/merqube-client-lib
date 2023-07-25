"""
Create an equity basket index
"""
import json
import logging
import os
from typing import Final

import click

from merqube_client_lib.logging import get_module_logger
from merqube_client_lib.templates.equity_baskets.decrement_create import (
    DecrementIndexCreator as DC,
)
from merqube_client_lib.templates.equity_baskets.multieb_create import (
    MultiEquityBasketIndexCreator as MEB,
)
from merqube_client_lib.templates.equity_baskets.sstr_create import SSTRCreator as SSTR
from merqube_client_lib.templates.equity_baskets.util import EquityBasketIndexCreator

SUPPORTED_INDEX_TYPES: Final[list[str]] = ["decrement", "single_stock_total_return", "multiple_equity_basket"]

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
@click.option(
    "--poll",
    type=click.IntRange(0, 10),
    required=False,
    default=0,
    help="if this is set, this client will wait up to X minutes for the index launch to be successful. It will poll the index status via the API and report on the results. If this is not set, you can use the client to check the status manually",
)
def main(index_type: str, config_file_path: str, prod_run: bool, poll: int) -> None:
    """main entrypoint"""
    assert os.path.exists(config_file_path), f"Config file path does not exist: {config_file_path}"
    try:
        config = json.load(open(config_file_path, "r"))
    except json.JSONDecodeError as err:
        logger.exception(f"Failed to parse config file: {config_file_path}")
        raise err

    cls: EquityBasketIndexCreator
    match index_type:
        case "decrement":
            cls = DC()
        case "single_stock_total_return":
            cls = SSTR()
        case _:
            # "multiple_equity_basket"
            cls = MEB()

    cls.create(config=config, prod_run=prod_run, poll=poll)


if __name__ == "__main__":  # pragma: no cover
    main()  # pyright: ignore  # pylint: disable=no-value-for-parameter
