from copy import deepcopy

import pytest
from freezegun import freeze_time

from merqube_client_lib.templates.equity_baskets.sstr_create import SSTRCreator
from tests.conftest import mock_secapi

from .helpers import eb_test, eb_test_bad

cal = {"swaps_monitor_codes": ["LnB"], "calendar_identifiers": ["MIC:XPAR"]}

expected_no_ticker = {
    "administrative": {"role": "development"},
    "base_date": "2000/01/04",
    "currency": "EUR",
    "description": "SSEB 1",
    "family": "MerQube Single Stock TR indices",
    "family_description": "MerQube Single Stock TR indices",
    "identifiers": [],
    "launch_date": "2023/06/01",
    "name": "TEST_1",
    "namespace": "test",
    "related": [],
    "run_configuration": {
        "index_reports": [
            {
                "uuid": "e79c6ea1-2ad0-429c-a4f0-b89915c1839e",
                "program_args": {
                    "diss_config": '{\\"email\\": [{\\"files\\": [\\"levels\\", \\"close_portfolio\\", \\"corporate_actions\\", \\"proforma_portfolio\\"], \\"subject\\": \\"{INDEX_NAME} Report: {REPORT_DATE:%Y-%m-%d}\\"}]}'
                },
            }
        ],
        "job_enabled": True,
        "pod_image_and_tag": "merq-310:latest",
        "schedule": {"retries": 25, "retry_interval_min": 10, "schedule_start": "2023-05-27T18:00:00"},
        "tzinfo": "US/Eastern",
        "num_days_to_load": 100,
    },
    "spec": {
        "index_class": "merq.indices.merqube.equity.EquityBasketIndex",
        "index_class_args": {
            "spec": {
                "base_date": "2000-01-04",
                "base_val": 1000,
                "corporate_actions": {
                    "dividend": {"deduct_tax": False, "reinvest_day": "PREV_DAY", "reinvest_strategy": "IN_INDEX"}
                },
                "currency": "EUR",
                "index_id": "TEST_1",
                "portfolios": {
                    "constituents": [{"date": "2000-01-04", "identifier": "LVMH.PA", "quantity": 1}],
                    "date_type": "ROLL",
                    "identifier_type": "RIC",
                    "quantity_type": "WEIGHT",
                    "specification_type": "INLINE",
                },
                "holiday_spec": cal,
                "calendar": cal,
            }
        },
    },
    "stage": "prod",
    "title": "TEST_1",
}


expected_with = deepcopy(expected_no_ticker)
expected_with["identifiers"] = [{"name": "xxx", "provider": "bloomberg"}]


good_config = {
    "base_date": "2000-01-04",
    "base_value": 1000,
    "currency": "EUR",
    "description": "SSEB 1",
    "holiday_calendar": {"swaps_monitor_codes": ["LnB"], "mics": ["XPAR"]},
    "name": "TEST_1",
    "namespace": "test",
    "run_hour": 18,
    "run_minute": 0,
    "timezone": "US/Eastern",
    "title": "TEST_1",
    "ric": "LVMH.PA",
}

expected_bbg_post = {
    "index_name": "TEST_1",
    "name": "xxx",
    "namespace": "test",
    "ticker": "xxx",
    "metric": "price_return",
}


@freeze_time("2023-06-01")
@pytest.mark.parametrize(
    "bbg_ticker,expected,expected_bbg_post",
    [(None, expected_no_ticker, None), ("xxx", expected_with, expected_bbg_post)],
    ids=["no_ticker", "with_ticker"],
)
def test_ss_tr(bbg_ticker, expected, expected_bbg_post, v1_ss, monkeypatch):
    def _get_collection_single(*args, **kwargs):
        return v1_ss

    mock_secapi(
        monkeypatch,
        method_name_function_map={},
        session_func_map={"get_collection_single": _get_collection_single},
    )

    eb_test(
        cls=SSTRCreator,
        config=good_config,
        bbg_ticker=bbg_ticker,
        expected=expected,
        expected_bbg_post=expected_bbg_post,
    )


bad_1 = deepcopy(good_config)
del bad_1["ric"]

bad_2 = deepcopy(good_config)
bad_2["base_date"] = "2000REEEEEEE"


bad_3 = deepcopy(good_config)
bad_3["run_hour"] = 184

bad_4 = deepcopy(good_config)
bad_4["run_minute"] = 184


@pytest.mark.parametrize("case", [bad_1, bad_2, bad_3, bad_4])
def test_multi_bad(case, v1_ss, monkeypatch):
    eb_test_bad(cls=SSTRCreator, config=case, template=v1_ss, monkeypatch=monkeypatch)
