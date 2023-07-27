import os
from copy import deepcopy
from unittest.mock import ANY, MagicMock, call

import pandas as pd
import pytest
from freezegun import freeze_time

from merqube_client_lib.pydantic_types import (
    IdentifierUUIDPost,
    IndexDefinitionPost,
    Provider,
)
from merqube_client_lib.templates.equity_baskets.multieb_create import (
    MultiEquityBasketIndexCreator as MEB,
)
from merqube_client_lib.templates.equity_baskets.schema import ClientIndexConfigBase
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
    "launch_date": "2023/06/01",  # from freeze_time
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
        cls=MEB,
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
    eb_test_bad(cls=MEB, config=case, monkeypatch=monkeypatch, template=v1_multi)


iinfo = {
    "base_value": 100,
    "namespace": "testns",
    "name": "testname",
    "title": "testtitle",
    "base_date": "2022-01-01",
    "description": "testdesc",
    "run_hour": 16,
    "run_minute": 0,
}

iinfo = ClientIndexConfigBase.parse_obj(iinfo)


def _get_client():
    ident = MagicMock()
    index = MagicMock()
    target = MagicMock()

    class FakeClient:
        create_identifier = ident
        create_index = index
        replace_target_portfolio = target

    return FakeClient(), ident, index, target


def test_prod_run(v1_multi):
    manifest = deepcopy(v1_multi)
    del manifest["id"]
    del manifest["status"]
    ind = IndexDefinitionPost.parse_obj(manifest)

    client, ident, index, target = _get_client()
    MEB()._create_index(
        client=client,
        template=ind,
        index_info=iinfo,
        inner_spec={},
        prod_run=True,
    )

    assert ident.call_args_list == []
    assert index.call_args_list == [call(index_def=ANY)]
    assert target.call_args_list == []


def test_prod_run_ticker(v1_multi):
    manifest = deepcopy(v1_multi)
    del manifest["id"]
    del manifest["status"]
    ind = IndexDefinitionPost.parse_obj(manifest)

    inf = deepcopy(iinfo)
    inf.bbg_ticker = "TEST"

    client, ident, index, target = _get_client()
    MEB()._create_index(
        client=client,
        template=ind,
        index_info=inf,
        inner_spec={},
        prod_run=True,
    )

    assert ident.call_args_list == [
        call(
            provider=Provider.bloomberg,
            identifier_post=IdentifierUUIDPost(index_name="testname", name="TEST", namespace="testns", ticker="TEST"),
        )
    ]
    assert index.call_args_list == [call(index_def=ANY)]
    assert target.call_args_list == []


def test_prod_run_ticker_tp(v1_multi):
    manifest = deepcopy(v1_multi)
    del manifest["id"]
    del manifest["status"]
    ind = IndexDefinitionPost.parse_obj(manifest)
    ind.spec.index_class_args["spec"]["portfolios"]["constituents"] = [
        {"date": "2023-06-12", "identifier": "AA.N", "quantity": 1, "security_type": "EQUITY"},
        {"date": "2023-06-12", "identifier": "AAPL.OQ", "quantity": 2, "security_type": "EQUITY"},
        {"date": "2023-06-13", "identifier": "AA.N", "quantity": 2, "security_type": "EQUITY"},
        {"date": "2023-06-13", "identifier": "USD", "quantity": 100000000, "security_type": "CASH"},
    ]

    inf = deepcopy(iinfo)
    inf.bbg_ticker = "TEST"

    client, ident, index, target = _get_client()
    MEB()._create_index(
        client=client,
        template=ind,
        index_info=inf,
        inner_spec={},
        initial_target_portfolios=MEB()._inline_to_tp(ind.spec.index_class_args["spec"]["portfolios"]),
        prod_run=True,
    )

    assert ident.call_args_list == [
        call(
            provider=Provider.bloomberg,
            identifier_post=IdentifierUUIDPost(index_name="testname", name="TEST", namespace="testns", ticker="TEST"),
        )
    ]
    assert index.call_args_list == [call(index_def=ANY)]
    assert target.call_args_list == [
        call(
            index_id=ANY,
            target_portfolio={
                "positions": [
                    {"amount": 1.0, "asset_type": "EQUITY", "identifier": "AA.N", "identifier_type": "RIC"},
                    {"amount": 2.0, "asset_type": "EQUITY", "identifier": "AAPL.OQ", "identifier_type": "RIC"},
                ],
                "timestamp": "2023-06-12T00:00:00",
                "unit_of_measure": "SHARES",
            },
        ),
        call(
            index_id=ANY,
            target_portfolio={
                "positions": [
                    {"amount": 2.0, "asset_type": "EQUITY", "identifier": "AA.N", "identifier_type": "RIC"},
                    {
                        "amount": 100000000.0,
                        "asset_type": "CASH",
                        "identifier": "USD",
                        "identifier_type": "CURRENCY_CODE",
                    },
                ],
                "timestamp": "2023-06-13T00:00:00",
                "unit_of_measure": "SHARES",
            },
        ),
    ]
