import os
from copy import deepcopy

import pandas as pd
import pytest
from freezegun import freeze_time

from merqube_client_lib.templates.equity_baskets.multiple_equity_basket import create
from tests.conftest import mock_secapi

from .helpers import eb_test, eb_test_bad

here = os.path.dirname(os.path.abspath(__file__))

cal = {"calendar_identifiers": ["MIC:XNYS"]}

expected_base = {
    "administrative": {"role": "calculation"},
    "base_date": "2000/01/04",
    "currency": "EUR",
    "description": "wonderful index",
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
        "index_reports": [
            {
                "uuid": "da6057c3-d78e-4975-b1d4-dc40f3c67c83",
                "program_args": {
                    "diss_config": '{\\"s3\\": [{\\"bucket\\": \\"merq-dissemination-backups\\", \\"key_prefix\\": \\"bloomberg\\", \\"files\\": [\\"bloomberg_portfolio\\"]}], \\"sftp\\": [{\\"files\\": [\\"bloomberg_portfolio\\"], \\"sftp_targets\\": [\\"5f150574-48d4-44c4-b0e0-f92d8956fa6b\\"]}], \\"email\\": [{\\"files\\": [\\"close_portfolio\\", \\"open_portfolio\\", \\"corporate_actions\\", \\"proforma_portfolio\\"], \\"subject\\": \\"{INDEX_NAME} Index Report {REPORT_DATE:%Y-%m-%d}\\"}]}'
                },
            }
        ],
        "job_enabled": True,
        "pod_image_and_tag": "merq-310:latest",
        "schedule": {"retries": 25, "retry_interval_min": 10, "schedule_start": "2023-05-27T18:00:00"},
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
                    "constituents": [],
                    "date_type": "EFFECTIVE",
                    "identifier_type": "RIC",
                    "quantity_type": "SHARES",
                    "specification_type": "API",
                },
                "valid_mics": ["XNYS", "XNAS", "ARCX"],
                "holiday_spec": cal,
                "calendar": cal,
            }
        },
    },
    "stage": "prod",
    "tags": "custom",
    "title": "TEST_1",
}

expected_tp = [
    (
        pd.Timestamp("2000-01-04 00:00:00"),
        {
            "positions": [
                {"amount": 100.0, "asset_type": "CASH", "identifier": "USD", "identifier_type": "CURRENCY_CODE"}
            ],
            "timestamp": "2000-01-04T00:00:00",
            "unit_of_measure": "SHARES",
        },
    ),
    (
        pd.Timestamp("2022-03-11 00:00:00"),
        {
            "positions": [
                {"amount": -0.2512355, "asset_type": "EQUITY", "identifier": "AAPL.OQ", "identifier_type": "RIC"},
                {
                    "amount": -0.28782633781297995,
                    "asset_type": "EQUITY",
                    "identifier": "AMZN.OQ",
                    "identifier_type": "RIC",
                },
                {"amount": 0.78687756527879, "asset_type": "EQUITY", "identifier": "GOOG.OQ", "identifier_type": "RIC"},
                {"amount": 0.8687756527878999, "asset_type": "EQUITY", "identifier": "A.N", "identifier_type": "RIC"},
                {"amount": 60.0, "asset_type": "CASH", "identifier": "USD", "identifier_type": "CURRENCY_CODE"},
            ],
            "timestamp": "2022-03-11T00:00:00",
            "unit_of_measure": "SHARES",
        },
    ),
]

expected_bbg_post = {"index_name": "TEST_1", "name": "xxx", "namespace": "test", "ticker": "xxx"}

good_config = {
    "base_date": "2000-01-04",
    "base_value": 100,
    "constituents_csv_path": os.path.join(here, "portfolios.csv"),
    "currency": "EUR",
    "description": "wonderful index",
    "name": "TEST_1",
    "namespace": "test",
    "run_hour": 18,
    "run_minute": 0,
    "timezone": "US/Eastern",
    "title": "TEST_1",
    "holiday_calendar": {"mics": ["XNYS"], "swaps_monitor_codes": []},
}


@freeze_time("2023-06-01")  # for schedule-start
@pytest.mark.parametrize("intraday", [True, False], ids=["intraday", "eod"])
@pytest.mark.parametrize(
    "corax_conf, has_corax",
    [(None, True), ({"reinvest_dividends": True}, True), ({"reinvest_dividends": False}, False)],
    ids=["corax_implicit", "corax_explicit", "corax-false"],
)
@pytest.mark.parametrize("bbg_ticker", ["xxx", None], ids=["with_bbg", "without_bbg"])
def test_multi(intraday, bbg_ticker, corax_conf, has_corax, v1_multi, monkeypatch):
    expected = deepcopy(expected_base)
    ebbg = None

    if has_corax:
        expected["spec"]["index_class_args"]["spec"]["corporate_actions"] = {
            "dividend": {"deduct_tax": False, "reinvest_day": "PREV_DAY", "reinvest_strategy": "IN_INDEX"}
        }

    if intraday:
        expected["intraday"]["enabled"] = True
        if bbg_ticker:
            expected["intraday"]["publish_config"]["price_return"].append({"target": "bloomberg"})

    if bbg_ticker:
        expected["identifiers"] = [{"name": bbg_ticker, "provider": "bloomberg"}]
        ebbg = expected_bbg_post

    def _get_collection_single(*args, **kwargs):
        return v1_multi

    mock_secapi(
        monkeypatch,
        method_name_function_map={},
        session_func_map={"get_collection_single": _get_collection_single},
    )

    eb_test(
        func=create.create,
        config=good_config,
        bbg_ticker=bbg_ticker,
        expected=expected,
        expected_bbg_post=ebbg,
        intraday=intraday,
        expected_target_portfolios=expected_tp,
        corax_conf=corax_conf,
    )


bad_1 = {
    "base_date": "2000-01-04",
    "base_value": 100,
    "currency": "EUR",
    "description": "wonderful index",
    "name": "TEST_1",
    "namespace": "test",
    "run_hour": 18,
    "run_minute": 0,
    "timezone": "US/Eastern",
    "title": "TEST_1",
}


@pytest.mark.parametrize("case", [bad_1])
def test_multi_bad(case, v1_multi, monkeypatch):
    eb_test_bad(func=create.create, config=case, monkeypatch=monkeypatch, template=v1_multi)
