"""
Replace the portfolio of an equity basket index (or post future portfolios)
"""
import os

import click
import pandas as pd

from merqube_client_lib.api_client.merqube_client import MerqubeAPIClientSingleIndex
from merqube_client_lib.logging import get_module_logger
from merqube_client_lib.templates.equity_baskets.multiple_equity_basket.base import (
    get_constituents,
    inline_to_tp,
)
from merqube_client_lib.templates.equity_baskets.util import get_inner_spec, read_file
from merqube_client_lib.util import get_token, pydantic_to_dict

logger = get_module_logger(__name__)


def _update_portfolio(
    index_name: str, constituents_csv_path: str, level_overrides_csv_path: str | None = None, prod_run: bool = False
) -> None:
    """
    Creates a new Equity Basket with multiple entries
    """
    client = MerqubeAPIClientSingleIndex(index_name=index_name, token=get_token())
    template = client.model

    ports = {
        "constituents": get_constituents(constituents_csv_path=constituents_csv_path),
        "date_type": "EFFECTIVE",
        "identifier_type": "RIC",
        "quantity_type": "SHARES",
        "specification_type": "API",
    }

    target_portfolios = inline_to_tp(ports)

    if level_overrides_csv_path:
        inner_spec = get_inner_spec(template=template)
        inner_spec["level_overrides"] = read_file(level_overrides_csv_path)

    if not prod_run:
        logger.debug("Dry run, not updating portfolio")
        return

    logger.info("Updating portfolio")
    # in the ongoing update case, we only care about dates >= today since all history is
    # already in on the server, and not relevent to the next run of the index
    today = pd.Timestamp.today()
    for date, tp in target_portfolios:
        if date >= today:
            # see the docstring under replace_target_portfolio; this works for future dates too, desptie 'replace'
            client.replace_portfolio(target_portfolio=pydantic_to_dict(tp))
        else:
            logger.warning(f"Ignoring portfolio dated in the past, {date}, since it will have no effect")


@click.command()
@click.option("--index-name", type=str, required=True, help="the index name to update")
@click.option("--constituents-csv-path", type=str, required=True, help="path to the constituents csv file")
@click.option(
    "--level_overrides_csv_path",
    type=str,
    required=False,
    help="path to a level overrides csv file, if applicable (not required)",
)
@click.option("--prod-run", is_flag=True, default=False, help="Create the index in production")
def main(
    index_name: str, constituents_csv_path: str, level_overrides_csv_path: str | None = None, prod_run: bool = False
) -> None:
    """main entrypoint"""
    assert os.path.exists(constituents_csv_path), f"Constituents csv file does not exist: {constituents_csv_path}"
    if level_overrides_csv_path:
        assert os.path.exists(
            level_overrides_csv_path
        ), f"Level overrides csv file does not exist: {level_overrides_csv_path}"
    _update_portfolio(index_name=index_name, constituents_csv_path=constituents_csv_path, prod_run=prod_run)


if __name__ == "__main__":
    main()  # pyright: ignore  # pylint: disable=no-value-for-parameter
