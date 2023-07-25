import os

import pandas as pd

from merqube_client_lib.templates.equity_baskets.multieb_create import (
    MultiEquityBasketIndexCreator,
)
from merqube_client_lib.util import pydantic_to_dict

here = os.path.dirname(os.path.abspath(__file__))


def test_inline_to_tp():
    constituents_csv_path = os.path.join(here, "portfolios.csv")

    cr = MultiEquityBasketIndexCreator()

    ports = {
        "constituents": cr._get_constituents(
            constituents_csv_path=constituents_csv_path,
            base_date=pd.Timestamp("2000-01-04"),
            base_value=100.0,
            add_initial_cash_position=True,
        ),
        "date_type": "EFFECTIVE",
        "identifier_type": "RIC",
        "quantity_type": "SHARES",
        "specification_type": "API",
    }

    tp = cr._inline_to_tp(ports)

    assert [(X, pydantic_to_dict(Y)) for X, Y in tp] == [
        (
            pd.Timestamp("2000-01-04"),
            {
                "positions": [
                    {"amount": 100.0, "asset_type": "CASH", "identifier": "USD", "identifier_type": "CURRENCY_CODE"}
                ],
                "timestamp": "2000-01-04T00:00:00",
                "unit_of_measure": "SHARES",
            },
        ),
        (
            pd.Timestamp("2022-03-11"),
            {
                "positions": [
                    {
                        "amount": -0.2512355,
                        "asset_type": "EQUITY",
                        "identifier": "AAPL.OQ",
                        "identifier_type": "RIC",
                    },
                    {
                        "amount": -0.28782633781297995,
                        "asset_type": "EQUITY",
                        "identifier": "AMZN.OQ",
                        "identifier_type": "RIC",
                    },
                    {
                        "amount": 0.78687756527879,
                        "asset_type": "EQUITY",
                        "identifier": "GOOG.OQ",
                        "identifier_type": "RIC",
                    },
                    {
                        "amount": 0.8687756527878999,
                        "asset_type": "EQUITY",
                        "identifier": "A.N",
                        "identifier_type": "RIC",
                    },
                    {"amount": 60.0, "asset_type": "CASH", "identifier": "USD", "identifier_type": "CURRENCY_CODE"},
                ],
                "timestamp": "2022-03-11T00:00:00",
                "unit_of_measure": "SHARES",
            },
        ),
    ]
