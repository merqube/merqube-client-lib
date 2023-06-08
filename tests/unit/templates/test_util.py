import json
import os
import tempfile
from unittest.mock import MagicMock

from merqube_client_lib.templates.equity_baskets.multiple_no_corax import create
from merqube_client_lib.templates.equity_baskets.util import inline_to_tp
from tests.conftest import mock_secapi

here = os.path.dirname(os.path.abspath(__file__))


def test_inline_to_tp(v1_multi, monkeypatch):
    mock_secapi(
        monkeypatch,
        method_name_function_map={},
        session_func_map={"get_collection_single": MagicMock(return_value=v1_multi)},
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        with open((fpath := os.path.join(tmpdir, "test.json")), "w") as f:
            f.write(
                json.dumps(
                    {
                        "base_date": "2000-01-04",
                        "base_value": 100,
                        "constituents_csv_path": os.path.join(here, "portfolios.csv"),
                        "currency": "EUR",
                        "description": "SSEB 1",
                        "name": "TEST_1",
                        "namespace": "test",
                        "run_hour": 18,
                        "run_minute": 0,
                        "timezone": "US/Eastern",
                        "title": "TEST_1",
                    }
                )
            )

        template, _ = create.create(config_file_path=fpath)
        assert [(y, json.loads(x.json(exclude_none=True))) for (y, x) in inline_to_tp(template)] == [
            (
                "2000-01-04",
                {
                    "positions": [
                        {"amount": 100.0, "asset_type": "CASH", "identifier": "USD", "identifier_type": "CURRENCY_CODE"}
                    ],
                    "timestamp": "2000-01-04",
                    "unit_of_measure": "UNITS",
                },
            ),
            (
                "2022-03-11",
                {
                    "positions": [
                        {
                            "amount": -0.2512355,
                            "asset_type": "EQUITY",
                            "identifier": "AAPL.OQ",
                            "identifier_type": "RIC",
                            "use_primary_listing": False,
                        },
                        {
                            "amount": -0.28782633781297995,
                            "asset_type": "EQUITY",
                            "identifier": "AMZN.OQ",
                            "identifier_type": "RIC",
                            "use_primary_listing": False,
                        },
                        {
                            "amount": 0.78687756527879,
                            "asset_type": "EQUITY",
                            "identifier": "GOOG.OQ",
                            "identifier_type": "RIC",
                            "use_primary_listing": False,
                        },
                        {
                            "amount": 0.8687756527878999,
                            "asset_type": "EQUITY",
                            "identifier": "A.N",
                            "identifier_type": "RIC",
                            "use_primary_listing": False,
                        },
                        {"amount": 60.0, "asset_type": "CASH", "identifier": "USD", "identifier_type": "CURRENCY_CODE"},
                    ],
                    "timestamp": "2022-03-11",
                    "unit_of_measure": "UNITS",
                },
            ),
        ]
