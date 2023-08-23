"""
Replace the portfolio of an equity basket index (or post future portfolios)
"""
import os

import click
import pandas as pd

from merqube_client_lib.api_client.merqube_client import MerqubeAPIClientSingleIndex
from merqube_client_lib.logging import get_module_logger
from merqube_client_lib.pydantic_v2_types import (
    ClientMultiEBPortUpdate,
    ClientTemplateResponse,
)
from merqube_client_lib.templates.equity_baskets.creators import read_file
from merqube_client_lib.util import get_token

logger = get_module_logger(__name__)


def _update_portfolio(index_name: str, constituents_csv_path: str, staging: bool, prod_run: bool = False) -> None:
    """
    Creates a new Equity Basket with multiple entries
    """
    client = MerqubeAPIClientSingleIndex(
        index_name=index_name, token=get_token(), prefix_url="https://staging.api.merqube.com" if staging else None
    )
    payload = {"constituents": read_file(filename=constituents_csv_path)}
    ClientMultiEBPortUpdate.parse_obj(payload)

    res = client.session.post(
        "/helper/index-template/multi_eb_portfolios",
        json={"constituents": read_file(filename=constituents_csv_path)},
    ).json()

    target_portfolios = ClientTemplateResponse.parse_obj(res).target_ports
    if not target_portfolios:
        logger.warning("No target portfolios returned")
        return

    if not prod_run:
        logger.debug("Dry run, not updating portfolio")
        return

    logger.info("Updating portfolio")
    # in the ongoing update case, we only care about dates >= today since all history is
    # already in on the server, and not relevent to the next run of the index

    today = pd.Timestamp.utcnow().date().isoformat()
    target_portfolios = [tp for tp in target_portfolios if tp.timestamp >= today]
    client.replace_portfolio(target_portfolio=target_portfolios)


@click.command()
@click.option("--index-name", type=str, required=True, help="the index name to update")
@click.option("--constituents-csv-path", type=str, required=True, help="path to the constituents csv file")
@click.option("--staging", is_flag=True, default=False, help="Create the index in staging")
@click.option("--prod-run", is_flag=True, default=False, help="Create the index in production")
def main(index_name: str, constituents_csv_path: str, staging: bool, prod_run: bool = False) -> None:
    """main entrypoint"""
    assert os.path.exists(constituents_csv_path), f"Constituents csv file does not exist: {constituents_csv_path}"
    _update_portfolio(
        index_name=index_name, constituents_csv_path=constituents_csv_path, staging=staging, prod_run=prod_run
    )


if __name__ == "__main__":
    main()  # pyright: ignore  # pylint: disable=no-value-for-parameter
