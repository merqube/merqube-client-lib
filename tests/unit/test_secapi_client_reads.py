from functools import partial
from unittest.mock import MagicMock, call

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from merqube_client_lib.api_client.merqube_client import get_client
from tests.conftest import mock_secapi
from tests.unit.fixtures.gsm_chunked_fixtures import (
    chunked_id,
    chunked_metric,
    non_chunked,
)
from tests.unit.fixtures.gsm_fixtures import (
    ID1,
    ID2,
    ID3,
    MULT_MULT_EXPECTED,
    MULT_SING_EXPECTED,
    SING_MULT_EXPECTED,
    SING_SING_EXPECTED,
    TEST_IDS,
    TEST_IDS_NE,
    TEST_METRICS,
    TEST_METRICS_NE,
    TEST_NAMES_NE,
    mult_mult_assertion,
    mult_sing_assertion,
    sing_mult_assertion,
    sing_sing_assertion,
)


def test_public_client():
    """test instantiating without credentials"""
    # twice to trigger cache
    public = get_client()
    public2 = get_client()
    assert public is public2


@pytest.mark.parametrize(
    "security_type",
    [("custom"), ("futures_contract"), ("futures_root"), ("index"), ("intraday_index"), ("fx"), ("interest_rate")],
    ids=["custom", "futures_contract", "futures_root", "index", "intraday_index", "fx", "interest_rate"],
)
def test_get_metrics_for_security(security_type):
    metrics = [
        {"data_type": "string", "description": "the name of the security", "name": "name"},
        {
            "data_type": "float64",
            "description": "Index value reflecting only the price performance of constituents.",
            "name": "price_return",
        },
    ]

    class FakeSession:
        def get_collection(self, url):
            if url == "/security":
                return [
                    {"name": "custom"},
                    {"name": "futures_contract"},
                    {"name": "futures_root"},
                    {"name": "index"},
                    {"name": "intraday_index"},
                    {"name": "fx"},
                    {"name": "interest_rate"},
                ]
            if url == f"/security/{security_type}/fake-id/metrics":
                return metrics
            raise Exception()

    result = get_client(user_session=FakeSession()).get_metrics_for_security(sec_type=security_type, sec_id="fake-id")
    assert result == metrics


def gsm_call(monkeypatch, fixture=None):
    mock_secapi(monkeypatch, method_name_function_map={})
    public = get_client()

    if fixture:
        public.session.get_collection = lambda url, options: fixture

    sm = partial(
        public.get_security_metrics,
        sec_type="index",
        start_date=pd.Timestamp("2023-04-27"),
        end_date=pd.Timestamp("2023-05-03"),
        addl_options={"as_of": "2023-05-04T12:00:00"},
    )

    return sm


@pytest.mark.parametrize(
    "expected, assertion",
    [
        (SING_SING_EXPECTED, sing_sing_assertion),
        (SING_MULT_EXPECTED, sing_mult_assertion),
        (MULT_SING_EXPECTED, mult_sing_assertion),
        (MULT_MULT_EXPECTED, mult_mult_assertion),
    ],
)
def test_get_security_metrics_no_chunks(expected, assertion, monkeypatch):
    """
    single security, single metric
    because these have no chunking, the output is equal to the get_security_metrics call
    the assertion functions are imported because the int tests use the same ones (without mocking)
    """
    sm = gsm_call(monkeypatch, expected)
    assertion(sm)


def test_multi_ids_multi_metrics_chunked_bad_values(monkeypatch):
    """
    illegal inputs
    """
    sm = gsm_call(monkeypatch)
    with pytest.raises(NotImplementedError):
        sm(
            sec_ids=TEST_IDS,
            metrics=TEST_METRICS,
            metrics_chunk_size=3,
            securities_chunk_size=3,
        )

    with pytest.raises(ValueError):
        sm(
            sec_ids=TEST_IDS,
            metrics=TEST_METRICS,
            securities_chunk_size=0,
        )

    with pytest.raises(ValueError):
        sm(
            sec_ids=TEST_IDS,
            metrics=TEST_METRICS,
            metrics_chunk_size=0,
        )

    with pytest.raises(ValueError):
        sm(
            sec_ids=TEST_IDS,
            metrics="foo",
            metrics_chunk_size=3,
        )

    with pytest.raises(ValueError):
        sm(
            sec_ids="foo",
            metrics=TEST_METRICS,
            securities_chunk_size=3,
        )

    with pytest.raises(ValueError):
        sm(
            sec_names="foo",
            metrics=TEST_METRICS,
            securities_chunk_size=3,
        )

    with pytest.raises(ValueError):
        sm(
            metrics=TEST_METRICS,
            securities_chunk_size=3,
        )


def chunked_gsm_call(monkeypatch, calls, mock_sec_call=True):
    public = get_client()

    if mock_sec_call:
        mock_secapi(monkeypatch, method_name_function_map={})

    coll = MagicMock(side_effect=calls)
    public.session.get_collection = coll

    sm = partial(
        public.get_security_metrics,
        sec_type="index",
        start_date=pd.Timestamp("2023-04-27"),
        end_date=pd.Timestamp("2023-05-03"),
        addl_options={"as_of": "2023-05-04T12:00:00"},
    )

    return sm, coll


def _get_non_chunked(monkeypatch, **kwargs):
    sm_non = gsm_call(monkeypatch, fixture=non_chunked)

    mult_mult = sm_non(**kwargs)

    assert len(mult_mult) == 15
    assert mult_mult.columns.tolist() == [
        "daily_return",
        "eff_ts",
        "id",
        "metricdoesnotexist",
        "name",
        "price_return",
        "total_return",
    ]

    # row order is not gauranteed to be preserved when chunking
    mult_mult = mult_mult.sort_values(["id", "eff_ts"]).reset_index().drop("index", axis=1)

    return mult_mult


def test_chunked_ids(monkeypatch):
    """
    There are many permutations of this test in the integration tests.
    However, since the mocking here is painful, we only test one complicated scenario.
    """
    kwargs = {"metrics": TEST_METRICS_NE}
    kwargs["sec_ids"] = TEST_IDS_NE

    mult_mult = _get_non_chunked(monkeypatch, **kwargs)

    sm, coll = chunked_gsm_call(monkeypatch, calls=chunked_id)

    chunked = sm(
        **kwargs,
        securities_chunk_size=2,
    )

    assert coll.call_args_list == [
        call(
            url="/security/index",
            # first two ids
            options={
                "metrics": "daily_return,price_return,total_return,metricdoesnotexist",
                "names": "",
                "ids": f"{ID1},{ID2}",
                "start_date": "2023-04-27T00:00:00",
                "end_date": "2023-05-03T00:00:00",
                "as_of": "2023-05-04T12:00:00",
            },
        ),
        call(
            url="/security/index",
            # second two ids
            options={
                "metrics": "daily_return,price_return,total_return,metricdoesnotexist",
                "names": "",
                "ids": f"{ID3},doesnotexist",
                "start_date": "2023-04-27T00:00:00",
                "end_date": "2023-05-03T00:00:00",
                "as_of": "2023-05-04T12:00:00",
            },
        ),
    ]
    assert_frame_equal(left=mult_mult, right=chunked, check_like=True)


def test_chunked_names(monkeypatch):
    """
    There are many permutations of this test in the integration tests.
    However, since the mocking here is painful, we only test one complicated scenario.
    """
    kwargs = {"metrics": TEST_METRICS_NE}
    kwargs["sec_names"] = TEST_NAMES_NE

    mult_mult = _get_non_chunked(monkeypatch, **kwargs)

    sm, coll = chunked_gsm_call(monkeypatch, calls=chunked_metric, mock_sec_call=False)

    chunked = sm(
        **kwargs,
        metrics_chunk_size=2,
    )

    assert coll.call_args_list == [
        call(
            url="/security/index",
            options={
                # first two metrics:
                "metrics": "daily_return,price_return",
                "names": "MQ2S0B04,MQ2Q0BQR,MQ2S0B01,doesnotexist",
                "ids": "",
                "start_date": "2023-04-27T00:00:00",
                "end_date": "2023-05-03T00:00:00",
                "as_of": "2023-05-04T12:00:00",
            },
        ),
        call(
            url="/security/index",
            options={
                # second two metrics:
                "metrics": "total_return,metricdoesnotexist",
                "names": "MQ2S0B04,MQ2Q0BQR,MQ2S0B01,doesnotexist",
                "ids": "",
                "start_date": "2023-04-27T00:00:00",
                "end_date": "2023-05-03T00:00:00",
                "as_of": "2023-05-04T12:00:00",
            },
        ),
    ]

    assert_frame_equal(left=mult_mult, right=chunked, check_like=True)


def test_mapping_table():
    """Tests mapping table of ids to names / names to ids"""

    class FakeSession:
        def get_collection(self, url, options=None):
            if url == "/security":
                return [
                    {"name": "index"},
                ]
            if url == "/security/index":
                return [{"name": "name1", "id": "id1"}, {"name": "name2", "id": "id2"}, {"name": "name3", "id": "id3"}]
            raise Exception(url)

    client = get_client(user_session=FakeSession())
    assert client.get_security_definitions_mapping_table(sec_type="index") == {
        "name1": "id1",
        "name2": "id2",
        "name3": "id3",
    }
    # name:id
    # id:name
    assert client.get_security_definitions_mapping_table(sec_type="index", sec_ids=["id1", "id2", "id3"]) == {
        "id1": "name1",
        "id2": "name2",
        "id3": "name3",
    }
