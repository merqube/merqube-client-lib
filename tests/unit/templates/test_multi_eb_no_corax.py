import json
import os
import tempfile
from copy import deepcopy
from unittest.mock import MagicMock

import pytest
from freezegun import freeze_time

from merqube_client_lib.templates.equity_baskets.multiple_no_corax import create
from tests.conftest import mock_secapi

here = os.path.dirname(os.path.abspath(__file__))


expected_no_ticker = {
    "administrative": {"role": "calculation"},
    "base_date": "2000/01/04",
    "description": "Template for Equity Baskets (non Corax)",
    "family": "Equity Baskets",
    "family_description": "Equity Baskets",
    "identifiers": [],
    "intraday": {
        "enabled": False,
        "ticker_period": 15.0,
        "tzinfo": "US/Eastern",
        "active_time_ranges": [{"start_time": "09:30:15", "end_time": "16:20", "exclude_holidays": True}],
        "publish_config": {"price_return": [{"target": "db"}, {"target": "secapi"}]},
        "calculation_max_retry_delay": 15,
    },
    "launch_date": "2099-01-01",
    "name": "TEST_1",
    "namespace": "test",
    "related": [],
    "run_configuration": {
        "index_reports": [],
        "job_enabled": True,
        "pod_image_and_tag": "merq-310:latest",
        "schedule": {"retries": 25, "retry_interval_min": 10, "schedule_start": "2023-05-30T18:00:00"},
        "tzinfo": "US/Eastern",
        "num_days_to_load": 0,
    },
    "spec": {
        "index_class": "merq.indices.merqube.equity.EquityBasketIndex",
        "index_class_args": {
            "spec": {
                "base_date": "2000-01-04",
                "base_val": 100,
                "corporate_actions": {"dividend": {"reinvest_strategy": "NONE"}},
                "index_id": "TEST_1",
                "level_overrides": [],
                "portfolios": {
                    "constituents": [
                        {"date": "2000-01-04", "identifier": "USD", "quantity": 100, "security_type": "CASH"},
                        {
                            "date": "2022-03-11",
                            "identifier": "AAPL.OQ",
                            "quantity": -0.2512355,
                            "security_type": "EQUITY",
                        },
                        {
                            "date": "2022-03-11",
                            "identifier": "AMZN.OQ",
                            "quantity": -0.28782633781297995,
                            "security_type": "EQUITY",
                        },
                        {
                            "date": "2022-03-11",
                            "identifier": "GOOG.OQ",
                            "quantity": 0.78687756527879,
                            "security_type": "EQUITY",
                        },
                        {
                            "date": "2022-03-11",
                            "identifier": "A.N",
                            "quantity": 0.8687756527878999,
                            "security_type": "EQUITY",
                        },
                        {"date": "2022-03-11", "identifier": "USD", "quantity": 60.0, "security_type": "CASH"},
                    ],
                    "date_type": "EFFECTIVE",
                    "identifier_type": "RIC",
                    "quantity_type": "SHARES",
                    "specification_type": "INLINE",
                },
                "valid_mics": ["XNYS", "XNAS", "ARCX"],
            }
        },
    },
    "stage": "prod",
    "tags": "custom",
    "title": "TEST_1",
}

expected_with = deepcopy(expected_no_ticker)
expected_with["identifiers"] = [{"name": "xxx", "provider": "bloomberg"}]

expected_no_ticker_intra = deepcopy(expected_no_ticker)
expected_no_ticker_intra["intraday"]["enabled"] = True
expected_no_ticker_intra["intraday"]["publish_config"]["price_return"] = [
    {"target": "db"},
    {"target": "secapi"},
]

expected_with_intra = deepcopy(expected_with)
expected_with_intra["intraday"]["enabled"] = True
expected_with_intra["intraday"]["publish_config"]["price_return"] = [
    {"target": "db"},
    {"target": "secapi"},
    {"target": "bloomberg"},
]

expected_bbg_post = {"index_name": "TEST_1", "name": "xxx", "namespace": "test", "ticker": "xxx"}

good_config = {
    "apikey": "xxx",
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


@freeze_time("2023-06-01")
@pytest.mark.parametrize(
    "intraday,bbg_ticker,expected,expected_bbg_post",
    [
        (False, None, expected_no_ticker, None),
        (True, None, expected_no_ticker_intra, None),
        (False, "xxx", expected_with, expected_bbg_post),
        (True, "xxx", expected_with_intra, expected_bbg_post),
    ],
)
def test_multi(intraday, bbg_ticker, expected, expected_bbg_post, monkeypatch):
    mock_secapi(
        monkeypatch,
        method_name_function_map={},
        session_func_map={
            "get_collection_single": MagicMock(return_value=json.load(open(os.path.join(here, "v1_multi.json")))),
        },
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        with open((fpath := os.path.join(tmpdir, "test.json")), "w") as f:
            conf = deepcopy(good_config)
            conf["bbg_ticker"] = bbg_ticker
            conf["is_intraday"] = intraday

            f.write(json.dumps(conf))

        template, bbg_post = create.create_equity_basket(config_file_path=fpath)
        assert json.loads(template.json(exclude_none=True)) == expected

        if not expected_bbg_post:
            assert bbg_post is None
        else:
            assert json.loads(bbg_post.json(exclude_none=True)) == expected_bbg_post


illegal_1 = {
    "apikey": "xxx",
    "base_date": "2000-01-04",
    "base_value": 100,
    "currency": "EUR",
    "description": "SSEB 1",
    "name": "TEST_1",
    "namespace": "test",
    "run_hour": 18,
    "run_minute": 0,
    "timezone": "US/Eastern",
    "title": "TEST_1",
}


@pytest.mark.parametrize("case", [illegal_1])
def test_multi_illegal(case, monkeypatch):
    mock_secapi(
        monkeypatch,
        method_name_function_map={},
        session_func_map={
            "get_collection_single": MagicMock(return_value=json.load(open(os.path.join(here, "v1_multi.json")))),
        },
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        with open((fpath := os.path.join(tmpdir, "test.json")), "w") as f:
            f.write(json.dumps(case))

        with pytest.raises(ValueError):
            create.create_equity_basket(config_file_path=fpath)
