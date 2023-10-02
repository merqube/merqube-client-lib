"""
Create an equity basket index
"""
import json
import logging
import os
from typing import Final

import click

from merqube_client_lib.logging import get_module_logger
from merqube_client_lib.templates.equity_baskets.creators import (
    DecrementIndexCreator as DC,
)
from merqube_client_lib.templates.equity_baskets.creators import (
    MultiEBIndexCreator as MEB,
)
from merqube_client_lib.templates.equity_baskets.creators import (
    SSTRIndexCreator as SSTR,
)
from merqube_client_lib.templates.options.creators import SimpleBufferCreator as SB

mapping = {"decrement": DC, "single_stock_total_return": SSTR, "multiple_equity_basket": MEB, "buffer_simple": SB}

SUPPORTED_INDEX_TYPES: Final = sorted(list(mapping.keys()))

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
@click.option("--staging", is_flag=True, default=False, help="Create the index in staging")
@click.option("--prod-run", is_flag=True, default=False, help="Create the index (without this, it is just templated)")
@click.option(
    "--poll",
    type=click.IntRange(0, 10),
    required=False,
    default=0,
    help="if this is set, this client will wait up to X minutes for the index launch to be successful. It will poll the index status via the API and report on the results. If this is not set, you can use the client to check the status manually",
)
def main(index_type: str, config_file_path: str, staging: bool, prod_run: bool, poll: int) -> None:
    """
    main entrypoint
    example usage:

        poetry run poetry run create --index-type=buffer_simple --config-file-path ~/Desktop/buffer.json --prod-run --poll 10
    """
    assert os.path.exists(config_file_path), f"Config file path does not exist: {config_file_path}"
    try:
        config = json.load(open(config_file_path, "r"))
    except json.JSONDecodeError as err:
        logger.exception(f"Failed to parse config file: {config_file_path}")
        raise err

    cls = mapping[index_type]
    obj = cls()

    if staging:
        obj.switch_to_staging()

    obj.create(config=config, prod_run=prod_run, poll=poll)


if __name__ == "__main__":  # pragma: no cover
    main()  # pyright: ignore  # pylint: disable=no-value-for-parameter
