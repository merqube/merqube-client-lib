from copy import deepcopy
from unittest.mock import MagicMock

import pandas as pd
import pytest
from freezegun import freeze_time

from merqube_client_lib.templates.equity_baskets import decrement_create as create
from tests.conftest import mock_secapi
from tests.unit.fixtures.test_tr_manifest_for_dec import tr

from .helpers import eb_test, eb_test_bad

TEST_RIC = "AXAF.PA"

expected_no_ticker = {
    "administrative": {"role": "development"},
    "base_date": "2000/01/04",
    "calc_freq": "Daily, EOD",
    "currency": "USD",
    "description": "DEC 1",
    "documents": {},
    "family": "merqube",
    "family_description": "",
    "identifiers": [],
    "launch_date": "2023/06/01",
    "name": "TEST_1",
    "namespace": "test",
    "plot_metric": "total_return",
    "related": [],
    "run_configuration": {
        "index_reports": [
            {
                "uuid": "4e37d683-0bee-4810-a852-f3d946da2e90",
                "program_args": {
                    "diss_config": '{\\"email\\": [{\\"subject\\": \\"{INDEX_NAME} Report: {DATE:%Y-%m-%d}\\"}]}',
                    "metric_name": "total_return",
                    "num_days": -1,
                },
            }
        ],
        "job_enabled": True,
        "pod_image_and_tag": "merq-310",
        "schedule": {"retries": 25, "retry_interval_min": 10, "schedule_start": "2023-05-27T18:00:00"},
        "tzinfo": "US/Eastern",
        "num_days_to_load": 0,
    },
    "spec": {
        "index_class": "merq.indices.merqube.overlay_index_ext.OverlayIndexExt",
        "index_class_args": {
            "spec": {
                "base_date": "2000-01-04",
                "base_val": 100.0,
                "day_count_convention": "f360",
                "fee": {"fee_value": 0.005, "fee_type": "percentage_pre"},
                "holiday_spec": {"calendar_identifiers": ["MQI:MQU_AXAF_TR_Index_Test_1"]},
                "index_id": "TEST_1",
                "metric": "price_return",
                "start_date": "2000-01-04",
                "underlying_ticker": "MQU_AXAF_TR_Index_Test_1",
            }
        },
    },
    "stage": "prod",
    "tags": "custom",
    "title": "TEST_1",
}
expected_diss_config = '{\\"email\\": [{\\"subject\\": \\"{INDEX_NAME} Report: {DATE:%Y-%m-%d}\\", \\"recipients\\": [\\"foo@co\\", \\"bar@co\\"]}]}'
expected_no_ticker_with_email = deepcopy(expected_no_ticker)
expected_no_ticker_with_email["run_configuration"]["index_reports"][0]["program_args"][
    "diss_config"
] = expected_diss_config


expected_with_ticker = deepcopy(expected_no_ticker)
expected_with_ticker["identifiers"] = [{"name": "xxx", "provider": "bloomberg"}]

expected_with_ticker_with_email = deepcopy(expected_with_ticker)
expected_with_ticker_with_email["run_configuration"]["index_reports"][0]["program_args"][
    "diss_config"
] = expected_diss_config

good_config = {
    "base_date": "2000-01-04",
    "description": "DEC 1",
    "ric": TEST_RIC,
    "name": "TEST_1",
    "namespace": "test",
    "run_hour": 18,
    "run_minute": 0,
    "timezone": "US/Eastern",
    "title": "TEST_1",
    "day_count_convention": "f360",
    "base_value": 100,
    "fee_value": 0.005,
    "fee_type": "percentage_pre",
}

expected_bbg_post = {"index_name": "TEST_1", "name": "xxx", "namespace": "test", "ticker": "xxx"}


@freeze_time("2023-06-01")
@pytest.mark.parametrize("base_value", [None, 1000, 100.0, 1])
@pytest.mark.parametrize(
    "bbg_ticker,email_list,expected,expec_bbg_post",
    [
        (None, None, expected_no_ticker, None),
        (None, ["foo@co", "bar@co"], expected_no_ticker_with_email, None),
        ("xxx", None, expected_with_ticker, expected_bbg_post),
        ("xxx", ["foo@co", "bar@co"], expected_with_ticker_with_email, expected_bbg_post),
    ],
    ids=["no_ticker", "no_ticker_with_email", "with_ticker", "with_ticker_with_email"],
)
def test_decrement(bbg_ticker, email_list, expected, expec_bbg_post, base_value, v1_decrement, monkeypatch):
    mock_secapi(
        monkeypatch,
        method_name_function_map={
            "get_indices_in_namespace": lambda namespace: [tr],
            "get_index_manifest": MagicMock(return_value=v1_decrement),
            "get_security_metrics": MagicMock(return_value=pd.DataFrame({"close": [100.0]})),
        },
    )

    def t():
        eb_test(
            func=create.create,
            config=good_config,
            bbg_ticker=bbg_ticker,
            email_list=email_list,
            expected=deepcopy(expected),
            expected_bbg_post=expec_bbg_post,
            base_value=base_value,
        )

    t()


bad_1 = deepcopy(good_config)
del bad_1["ric"]
b1 = (bad_1, "pydantic")

bad_2 = deepcopy(good_config)
bad_2["base_date"] = "2000REEEEEEE"
b2 = (bad_2, "pydantic")

bad_3 = deepcopy(good_config)
bad_3["fee_type"] = "noooo"
b3 = (bad_3, "pydantic")

bad_4 = deepcopy(good_config)
bad_4["fee_value"] = "noooo"
b4 = (bad_4, "pydantic")

bad_5 = deepcopy(good_config)
bad_5["start_date"] = "2000-01-01"
bad_5["base_date"] = "1999-01-02"
b5 = (bad_5, "The start date of the decrement index, if specified, must be before the base date")

bad_6 = deepcopy(good_config)
bad_6["email_list"] = [666]
b6 = (bad_6, "pydantic")

bad_7 = deepcopy(good_config)
bad_7["holiday_calendar"] = "noooo"
b7 = (bad_7, "pydantic")

bad_8 = deepcopy(good_config)
bad_8["timezone"] = "asdfnoooo"
b8 = (bad_8, "pydantic")

bad_9 = deepcopy(good_config)
bad_9["extraaaaaakeyyyyy"] = 1
b9 = (bad_9, "pydantic")


@pytest.mark.parametrize("case,err", [b1, b2, b3, b4, b5, b6, b7, b8, b9])
def test_multi_bad(case, err, v1_decrement, monkeypatch):
    actual = eb_test_bad(func=create.create, config=case, template=v1_decrement, monkeypatch=monkeypatch)
    if err == "pydantic":
        assert "pydantic.error_wrappers.ValidationError" in actual
    else:
        assert actual == f"ValueError: {err}"


disabled_tr = deepcopy(tr)
disabled_tr.run_configuration.job_enabled = False

no_rc_tr = deepcopy(tr)
no_rc_tr.run_configuration = None

diff_stock_tr = deepcopy(tr)
diff_stock_tr.spec.index_class_args["spec"]["portfolios"]["constituents"] = [
    {"date": "2005-12-30", "identifier": "NOOOOTAXAF.PA", "quantity": 1}
]

not_a_ss_tr = deepcopy(tr)
not_a_ss_tr.spec.index_class_args["spec"]["portfolios"]["constituents"] = [
    {"date": "2005-12-30", "identifier": "AXAF.PA", "quantity": 1},
    {"date": "2005-12-30", "identifier": "different", "quantity": 1},
]


@pytest.mark.parametrize(
    "inds, should_match",
    [
        ([tr], True),
        ([diff_stock_tr, tr], True),  # matches second
        ([disabled_tr], False),
        ([], False),
        ([no_rc_tr], False),
        ([diff_stock_tr], False),
        ([not_a_ss_tr], False),  # has two constituents
    ],
)
def test_get_trs(inds, should_match):
    """
    tests _tr_exists
    """

    class Cl:
        def get_indices_in_namespace(self, namespace):
            return inds

    res = create._tr_exists(Cl(), TEST_RIC)
    if should_match:
        assert res == "MQU_AXAF_TR_Index_Test_1"
    else:
        assert res is None
