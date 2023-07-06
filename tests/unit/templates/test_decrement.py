import os
from copy import deepcopy
from functools import partial

import pytest
from freezegun import freeze_time

from merqube_client_lib.templates.equity_baskets.decrement import create

from .helpers import eb_test, eb_test_bad

cal = {"calendar_identifiers": ["MIC:XNYS"]}

expected_no_ticker = {
    "administrative": {"role": "development"},
    "base_date": "2000/01/04",
    "calc_freq": "Daily, EOD",
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
                "holiday_spec": cal,
                "calendar": cal,
                "index_id": "TEST_1",
                "metric": "price_return",
                "output_metric": "total_return",
                "underlying_ticker": "MY_WONDERFUL_UNDERLYING_TR",
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
    "client_owned_underlying": False,
    "holiday_calendar": {"mics": ["XNYS"]},
    "name": "TEST_1",
    "namespace": "test",
    "run_hour": 18,
    "run_minute": 0,
    "timezone": "US/Eastern",
    "title": "TEST_1",
    "day_count_convention": "f360",
    "underlying_index_name": "MY_WONDERFUL_UNDERLYING_TR",
    "base_value": 100,
    "fee_value": 0.005,
    "fee_type": "percentage_pre",
}

expected_bbg_post = {"index_name": "TEST_1", "name": "xxx", "namespace": "test", "ticker": "xxx"}


def fake_s3_download(tdir, valid: bool = True):
    with open(p := os.path.join(tdir, "tr.csv"), "w") as f:
        f.write(
            "underlying_ric,index_name,metric\nZ.Y,TOMMY_EB_TEST_2,price_return\nLVMH.PA,MY_WONDERFUL_UNDERLYING_TR,price_return"
            if valid
            else ""
        )
    return p


def test_get_trs(monkeypatch):
    monkeypatch.setattr(
        "merqube_client_lib.templates.equity_baskets.decrement.create._download_tr_map", fake_s3_download
    )

    assert create._get_trs() == [
        {"underlying_ric": "LVMH.PA", "index_name": "MY_WONDERFUL_UNDERLYING_TR", "metric": "price_return"},
        {"underlying_ric": "Z.Y", "index_name": "TOMMY_EB_TEST_2", "metric": "price_return"},
    ]

    assert create._get_trs(tr="TOMMY_EB_TEST_2") == [
        {"underlying_ric": "Z.Y", "index_name": "TOMMY_EB_TEST_2", "metric": "price_return"},
    ]

    with pytest.raises(ValueError):
        create._get_trs(tr="TOMMY_EB_TEST_3")


fake_underlying = {
    "id": "123",
    "description": "test",
    "status": {"last_modified": "2020"},
    "title": "",
    "family": "",
    "administrative": {"role": "calculation"},
    "name": "t",
    "launch_date": "2020",
    "stage": "prod",
}


@freeze_time("2023-06-01")
@pytest.mark.parametrize("base_value", [None, 1000, 100.0, 1])
@pytest.mark.parametrize(
    "client_owned, should_work",
    [(False, True), (False, False), ("missing", False), (fake_underlying, True)],
    ids=["mqu", "missing-mqu", "invalid-client", "valid-client"],
)
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
def test_decrement(
    bbg_ticker, email_list, expected, expec_bbg_post, client_owned, should_work, v1_decrement, base_value, monkeypatch
):
    fake_s3 = partial(fake_s3_download, valid=(not client_owned and should_work))
    monkeypatch.setattr("merqube_client_lib.templates.equity_baskets.decrement.create._download_tr_map", fake_s3)

    def t():
        eb_test(
            func=create.create,
            config=good_config,
            bbg_ticker=bbg_ticker,
            email_list=email_list,
            expected=deepcopy(expected),
            template=v1_decrement,
            monkeypatch=monkeypatch,
            expected_bbg_post=expec_bbg_post,
            client_owned_underlying=client_owned,
            base_value=base_value,
        )

    if should_work:
        t()
    else:
        with pytest.raises(ValueError):
            t()


bad_1 = deepcopy(good_config)
del bad_1["underlying_index_name"]
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
bad_5["underlying_index_name"] = "nooot in file"
b5 = (bad_5, "nooot in file is not a valid TR")

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
    monkeypatch.setattr(
        "merqube_client_lib.templates.equity_baskets.decrement.create._download_tr_map", fake_s3_download
    )

    actual = eb_test_bad(func=create.create, config=case, template=v1_decrement, monkeypatch=monkeypatch)
    if err == "pydantic":
        assert "pydantic.error_wrappers.ValidationError" in actual
    else:
        assert actual == f"ValueError: {err}"
