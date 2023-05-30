import json
import os
import tempfile
from copy import deepcopy
from unittest.mock import MagicMock

import pytest

from merqube_client_lib.templates.equity_baskets.single_stock_total_return_corax import (
    create,
)
from tests.conftest import mock_secapi

here = os.path.dirname(os.path.abspath(__file__))


expected_no_ticker = {
    "administrative": {"role": "development"},
    "base_date": "2000-01-04",
    "description": "Template for TR indices",
    "family": "MerQube Single Stock TR indices",
    "family_description": "MerQube Single Stock TR indices",
    "identifiers": [],
    "launch_date": "2023/06/01",
    "name": "TEST_1",
    "namespace": "test",
    "related": [],
    "run_configuration": {
        "index_reports": [],
        "job_enabled": True,
        "pod_image_and_tag": "merq-310:latest",
        "schedule": {"retries": 25, "retry_interval_min": 10, "schedule_start": "2023-05-30T18:00:00"},
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
                    "dividend": {
                        "deduct_tax": False,
                        "reinvest_day": "PREV_DAY",
                        "reinvest_strategy": "IN_INDEX",
                    }
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
            }
        },
    },
    "stage": "prod",
    "title": "TEST_1",
}

expected_with = deepcopy(expected_no_ticker)
expected_with["identifiers"] = [{"name": "xxx", "provider": "bloomberg"}]


@pytest.mark.parametrize("bbg_ticker,expected", [(None, expected_no_ticker), ("xxx", expected_with)])
def test_ss_tr(bbg_ticker, expected, monkeypatch):
    mock_secapi(
        monkeypatch,
        method_name_function_map={},
        session_func_map={
            "get_collection_single": MagicMock(return_value=json.load(open(os.path.join(here, "v1_ss.json")))),
        },
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        with open((fpath := os.path.join(tmpdir, "test.json")), "w") as f:
            f.write(
                json.dumps(
                    {
                        "apikey": "xxx",
                        "base_date": "2000-01-04",
                        "bbg_ticker": bbg_ticker,
                        "currency": "EUR",
                        "description": "SSEB 1",
                        "name": "TEST_1",
                        "namespace": "test",
                        "run_hour": 18,
                        "run_minute": 0,
                        "timezone": "US/Eastern",
                        "title": "TEST_1",
                        "underlying_ric": "LVMH.PA",
                    }
                )
            )

        template = create.create_equity_basket(config_file_path=fpath)
        assert json.loads(template.json(exclude_none=True)) == expected


illegal_1 = {
    "apikey": "xxx",
    "base_date": "2000-01-04",
    "currency": "EUR",
    "description": "SSEB 1",
    "name": "TEST_1",
    "namespace": "test",
    "run_hour": 18,
    "run_minute": 0,
    "timezone": "US/Eastern",
    "title": "TEST_1",
}

illegal_2 = {
    "apikey": "xxx",
    "base_date": "2000REEEEEEE",
    "currency": "EUR",
    "description": "SSEB 1",
    "name": "TEST_1",
    "namespace": "test",
    "run_hour": 18,
    "run_minute": 0,
    "timezone": "US/Eastern",
    "title": "TEST_1",
    "underlying_ric": "LVMH.PA",
}


@pytest.mark.parametrize("case", [illegal_1, illegal_2])
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
