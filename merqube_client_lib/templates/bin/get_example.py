"""
Create an equity basket index
"""
import json

import click

from merqube_client_lib.templates.configs import (
    ClientBufferSimpleConfig,
    ClientDecrementConfig,
    ClientMultiEquityBasketConfig,
    ClientSSTRConfig,
)

mapping = {
    "decrement": ClientDecrementConfig,
    "single_stock_total_return": ClientSSTRConfig,
    "multiple_equity_basket": ClientMultiEquityBasketConfig,
    "buffer_simple": ClientBufferSimpleConfig,
}

supp = sorted(list(mapping.keys()))


@click.command()
@click.option(
    "--index-type",
    type=click.Choice(supp),
    required=True,
    help=f"type of index to create; must be one of {supp}",
)
def main(index_type: str) -> None:
    """
    Example usage:

        poetry run get_example --index-type multiple_equity_basket
        poetry run get_example --index-type buffer_simple

    """
    ex = mapping[index_type].get_example()  # type: ignore
    print(json.dumps(ex, indent=4))


if __name__ == "__main__":  # pragma: no cover
    main()  # pyright: ignore  # pylint: disable=no-value-for-parameter
