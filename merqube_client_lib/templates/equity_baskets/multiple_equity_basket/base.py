from typing import Any, cast

import pandas as pd

from merqube_client_lib.pydantic_types import (
    BasketPosition,
    EquityBasketPortfolio,
    PortfolioUom,
    RicEquityPosition,
)
from merqube_client_lib.templates.equity_baskets.util import read_file
from merqube_client_lib.types import TargetPortfoliosDates


def get_constituents(
    constituents_csv_path: str,
    base_date: str | pd.Timestamp | None = None,
    base_value: float | None = None,
    add_initial_cash_position: bool = False,
) -> list[dict[str, Any]]:
    """read and validate constituents file"""
    constituents = read_file(constituents_csv_path)

    if add_initial_cash_position:
        if not base_date or not base_value:
            raise ValueError("base_date and base_value must be set if add_initial_cash_position is True")

        if pd.Timestamp(base_date) >= pd.Timestamp(min(c["date"] for c in constituents)):
            raise ValueError("base_date should be set to a date at least one day before the first portfolio date")

        constituents += cast(
            dict[str, Any],
            [
                {
                    "date": base_date,
                    "identifier": "USD",
                    "quantity": base_value,
                    "security_type": "CASH",
                }
            ],
        )

    return constituents


def inline_to_tp(portfolio: dict[str, Any]) -> TargetPortfoliosDates:
    """
    Convert the inline portfolio to a list of target portfolios
    """

    target_portfolios: TargetPortfoliosDates = []

    uom = PortfolioUom.SHARES if portfolio["quantity_type"] == "SHARES" else PortfolioUom.WEIGHT
    id_type = portfolio["identifier_type"]

    # see how nany TP values we need
    dates = set()
    for constituent in (const := portfolio["constituents"]):
        dates.add(pd.Timestamp(constituent["date"]))

    for date in sorted(dates):
        positions: list[BasketPosition | RicEquityPosition] = []
        for constituent in const:
            sec_type = constituent["security_type"]
            pos_class = RicEquityPosition if sec_type == "EQUITY" else BasketPosition

            if pd.Timestamp(constituent["date"]) != date:
                continue  # will get picked up in another target portfolio

            positions.append(
                pos_class(
                    asset_type=constituent["security_type"],
                    identifier=constituent["identifier"],
                    amount=constituent["quantity"],
                    # this is only at the top level of inline; but its wrong for the cash position (in TP it is CURRENCY_CODE)
                    identifier_type="CURRENCY_CODE" if sec_type == "CASH" else id_type,
                )
            )

        target_port_val = EquityBasketPortfolio(timestamp=date, unit_of_measure=uom, positions=positions)  # type: ignore

        EquityBasketPortfolio.parse_obj(target_port_val)  # validate
        target_portfolios.append((date, target_port_val))

    return target_portfolios
