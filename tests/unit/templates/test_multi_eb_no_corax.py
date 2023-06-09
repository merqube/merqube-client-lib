import os
from copy import deepcopy

import pytest
from freezegun import freeze_time

from merqube_client_lib.templates.equity_baskets.multiple_no_corax import create

from .helpers import eb_test, eb_test_bad

here = os.path.dirname(os.path.abspath(__file__))

cal = {"calendar_identifiers": ["MIC:XNYS"], "weekmask": ["Mon", "Tue", "Wed", "Thu", "Fri"]}

expected_no_ticker = {
    "administrative": {"role": "calculation"},
    "base_date": "2000/01/04",
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
        "index_reports": ["8ba49d26-31eb-4918-8bee-6898e0941fe9", "33574191-914d-4de9-9ba1-050ad09d1ba9"],
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
                "holiday_spec": cal,
                "calendar": cal,
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
def test_multi(intraday, bbg_ticker, expected, expected_bbg_post, v1_multi, monkeypatch):
    eb_test(
        func=create.create,
        config=good_config,
        bbg_ticker=bbg_ticker,
        expected=expected,
        expected_bbg_post=expected_bbg_post,
        template=v1_multi,
        monkeypatch=monkeypatch,
        intraday=intraday,
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
