"""
Unit tests for indexapi
There are more in the integration tests
"""
from copy import deepcopy
from dataclasses import dataclass
from typing import Callable, cast
from unittest.mock import MagicMock, call

import pandas as pd
import pytest
from freezegun import freeze_time

from merqube_client_lib.api_client.merqube_client import (
    MerqubeAPIClientSingleIndex,
    get_client,
)
from merqube_client_lib.types import Manifest
from merqube_client_lib.util import pydantic_to_dict
from tests.conftest import mock_secapi
from tests.unit.fixtures.test_manifest import manifest

sid = "testid"

ret = [
    {"eff_ts": "2023-04-03T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2061.3759657505516},
    {"eff_ts": "2023-04-04T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2058.4726656406847},
    {"eff_ts": "2023-04-05T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2052.2820122315807},
    {"eff_ts": "2023-04-06T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2060.1335590375693},
    {"eff_ts": "2023-04-10T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2060.2625642018947},
]

exis_status = {
    "created_at": "2022-06-07T23:15:31.212502",
    "created_by": "test@merqube.com",
    "last_modified": "2023-01-25T22:40:25.552308",
    "last_modified_by": "test@merqube.com",
}


def test_single_index_returns(monkeypatch):
    """
    fixed (unit) example using:
    https://merqube.com/index/MQEFAB01
    https://api.merqube.com/index?name=MQEFAB01
    """

    def mock_get_collection(url, **kwargs):
        return (
            [{"name": "MQEFAB01", "id": sid}]
            if url == "https://api.merqube.com/index?name=MQEFAB01"
            else [{"name": "index"}]
        )  # get_security_metrics

    gsm = pd.DataFrame.from_records(ret)

    man = deepcopy(manifest)
    man["name"] = "MQEFAB01"
    man["id"] = sid

    mock_secapi(
        monkeypatch,
        method_name_function_map={"get_security_metrics": MagicMock(return_value=gsm)},
        session_func_map={"get_collection": mock_get_collection, "get_collection_single": MagicMock(return_value=man)},
        index_name="MQEFAB01",  # get_client_kwargs
    )

    client = get_client(index_name="MQEFAB01")

    df = client.get_returns(start_date=pd.Timestamp("2023-04-01"), end_date=pd.Timestamp("2023-04-10"))

    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert df.to_dict(orient="records") == ret

    with pytest.raises(ValueError):
        client.get_returns(
            start_date=pd.Timestamp("2023-04-01"), end_date=pd.Timestamp("2023-04-10"), use_intraday_metrics=True
        )


@dataclass
class ClientMocked:
    man: Manifest
    post: Callable
    get: Callable
    get_coll: Callable
    delete: Callable
    patch: Callable
    client: MerqubeAPIClientSingleIndex


def _setup(monkeypatch, with_name_call: bool = True, get_coll_return=[], lock: bool = False):
    ret = [[{"name": "MQEFAB01", "id": sid}], get_coll_return] if with_name_call else [get_coll_return]
    mock_get_collection = MagicMock(side_effect=ret)

    mock_post = MagicMock()
    mock_get = MagicMock()
    mock_delete = MagicMock()
    mock_patch = MagicMock()

    man = deepcopy(manifest)
    man["name"] = "MQEFAB01"
    man["id"] = sid

    if lock:
        man["status"]["locked_after"] = pd.Timestamp.now().isoformat()

    mock_secapi(
        monkeypatch,
        method_name_function_map={},
        session_func_map={
            "get_collection": mock_get_collection,
            "get_collection_single": MagicMock(return_value=man),
            "get_json": MagicMock(return_value=man),
            "patch": mock_patch,
            "post": mock_post,
            "get": mock_get,
            "delete": mock_delete,
        },
        index_name="MQEFAB01",  # get_client_kwargs
    )
    client = cast(MerqubeAPIClientSingleIndex, get_client(index_name="MQEFAB01"))
    return ClientMocked(man, mock_post, mock_get, mock_get_collection, mock_delete, mock_patch, client)


"""
For the below tests, there are integration tests that cover the actual functionality.
These are just unit testing the expected URLs
"""


@pytest.mark.parametrize(
    "method, expected_call",
    [
        ("get_portfolio", call("/index/testid/portfolio")),
        ("get_portfolio_allocations", call("/index/testid/portfolio_allocations")),
        ("get_caps", call("/index/testid/caps")),
        ("get_stats", call("/index/testid/stats")),
        ("get_data_collections", call("/index/testid/data_collections")),
    ],
)
def test_coll_methods(method, expected_call, monkeypatch):
    mocked = _setup(monkeypatch=monkeypatch, with_name_call=False, get_coll_return=[{"foo": "bar"}])
    func = getattr(mocked.client, method)
    assert func() == [{"foo": "bar"}]
    assert mocked.get_coll.call_args_list == [expected_call]


@pytest.mark.parametrize(
    "start_date, end_date",
    [
        (None, None),
        (pd.Timestamp("2023-04-01 01:02:03"), None),
        (None, pd.Timestamp("2023-04-01 04:05:06")),
        (pd.Timestamp("2023-04-01 01:02:03"), pd.Timestamp("2023-04-10 04:05:06")),
    ],
)
def test_get_target_portfolio(monkeypatch, start_date, end_date):
    mocked = _setup(monkeypatch=monkeypatch, with_name_call=False, get_coll_return=[{"foo": "bar"}])
    assert mocked.client.get_target_portfolio(start_date=start_date, end_date=end_date) == [{"foo": "bar"}]
    expected_opts = {}
    if start_date:
        expected_opts["start_date"] = start_date.isoformat()
    if end_date:
        expected_opts["end_date"] = end_date.isoformat()
    assert mocked.get_coll.call_args_list == [call("/index/testid/target_portfolio", options=expected_opts)]


def test_manifest_fetching(monkeypatch):
    mocked = _setup(monkeypatch=monkeypatch)
    cl = mocked.client
    assert cl.get_manifest() == mocked.man
    assert pydantic_to_dict(cl.model) == mocked.man


def test_from_existing(monkeypatch):
    mocked = _setup(monkeypatch=monkeypatch)
    template = deepcopy(mocked.man)
    del template["id"]
    del template["status"]
    template["name"] = "test"
    template["namespace"] = "test"
    assert pydantic_to_dict(mocked.client.post_model_from_existing()) == template


def test_update(monkeypatch):
    mocked = _setup(monkeypatch=monkeypatch)
    cl, mock_patch = mocked.client, mocked.patch

    # patch
    cl.partial_update(updates={"description": "test"}, auto_status=False)
    assert mock_patch.call_args_list == [call("/index/testid", json={"description": "test"})]  # (would fail irl)
    cl.partial_update(updates={"description": "test"})
    assert mock_patch.call_args_list == [
        call("/index/testid", json={"description": "test"}),
        call("/index/testid", json={"description": "test", "status": exis_status}),
    ]


@freeze_time(now := pd.Timestamp.now())
@pytest.mark.parametrize("already_locked", [True, False])
def test_lock(monkeypatch, already_locked):
    mocked = _setup(monkeypatch=monkeypatch, lock=already_locked)
    cl, mock_patch = mocked.client, mocked.patch

    # patch
    cl.lock_index(index_id="testid")
    assert (
        mock_patch.call_args_list == []
        if already_locked
        else [
            call(
                "/index/testid",
                json={
                    "status": {
                        "created_at": "2022-06-07T23:15:31.212502",
                        "created_by": "test@merqube.com",
                        "last_modified": "2023-01-25T22:40:25.552308",
                        "last_modified_by": "test@merqube.com",
                        "locked_after": (now + pd.Timedelta(seconds=3)).isoformat(),
                    }
                },
            )
        ]
    )


@pytest.mark.parametrize("already_unlocked", [True, False])
def test_unlock(already_unlocked, monkeypatch):
    mocked = _setup(monkeypatch=monkeypatch, lock=not already_unlocked)
    cl, mock_patch = mocked.client, mocked.patch

    # patch
    cl.unlock_index(index_id="testid")
    assert (
        mock_patch.call_args_list == []
        if already_unlocked
        else [
            call(
                "/index/testid",
                json={
                    "status": {
                        "created_at": "2022-06-07T23:15:31.212502",
                        "created_by": "test@merqube.com",
                        "last_modified": "2023-01-25T22:40:25.552308",
                        "last_modified_by": "test@merqube.com",
                    }
                },
            )
        ]
    )
