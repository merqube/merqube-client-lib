"""
Create an equity basket index
"""
import json
from typing import Final

import click

from merqube_client_lib.templates.equity_baskets.schema import (
    ClientDecrementConfig,
    ClientMultiEquityBasketConfig,
    ClientSSTRConfig,
)

SUPPORTED_INDEX_TYPES: Final[list[str]] = ["decrement", "single_stock_total_return", "multiple_equity_basket"]


@click.command()
@click.option(
    "--index-type",
    type=click.Choice(SUPPORTED_INDEX_TYPES),
    required=True,
    help=f"type of index to create; must be one of {SUPPORTED_INDEX_TYPES}",
)
def main(index_type: str) -> None:
    match index_type:
        case "decrement":
            ex = ClientDecrementConfig.get_example()
        case "single_stock_total_return":
            ex = ClientSSTRConfig.get_example()
        case _:
            ex = ClientMultiEquityBasketConfig.get_example()

    print(json.dumps(ex, indent=4))


if __name__ == "__main__":  # pragma: no cover
    main()  # pyright: ignore  # pylint: disable=no-value-for-parameter
