"""
Unit tests for indexapi
There are more in the integration tests
"""
from unittest.mock import MagicMock

import pandas as pd
import pytest

from merqube_client_lib.api_client.merqube_client import get_client
from tests.conftest import mock_secapi

valid1 = {"id": "valid1id", "name": "valid1", "stage": "prod"}
valid2 = {"id": "valid2id", "name": "valid2", "stage": "prod"}
valid3 = {"id": "valid3id", "name": "valid3", "stage": "test"}
valid = [valid1, valid2, valid3]


def test_get_all():
    def fake_get_collection(url, **kwargs):
        return valid if "type=all" in url else [x for x in valid if x["stage"] == "prod"]

    client = get_client()
    client.session.get_collection = fake_get_collection
    assert client.get_index_defs() == {k["id"]: k for k in valid if k["stage"] == "prod"}

    assert client.get_index_defs(include_nonprod=True) == {k["id"]: k for k in valid}


@pytest.mark.parametrize(
    "names,expected,inc_nonprod",
    [
        ("valid1,valid2", {"valid1id": valid1, "valid2id": valid2}, False),
        (["valid1", "valid2"], {"valid1id": valid1, "valid2id": valid2}, False),
        (
            ["valid1", "valid2", "valid3"],
            {"valid1id": valid1, "valid2id": valid2},
            False,
        ),  # without flag, valid3 is ignored
        (
            ["valid1", "valid2", "valid3"],
            {"valid1id": valid1, "valid2id": valid2, "valid3id": valid3},
            True,
        ),
        ("valid1", {"valid1id": valid1}, False),
        ("invalid", {}, False),
        ("valid1,invalid", {"valid1id": valid1}, False),
    ],
)
def test_get_indices(names, expected, inc_nonprod):
    def fake_get_collection(url, **kwargs):
        names = url.split("?names=")[1].split("&")[0].split(",")
        retl = [x for x in valid if x["name"] in names]
        return retl if "type=all" in url else [x for x in retl if x["stage"] == "prod"]

    client = get_client()
    client.session.get_collection = fake_get_collection

    assert client.get_index_defs(names, include_nonprod=inc_nonprod) == expected


def test_single_index_returns(monkeypatch):
    """
    fixed (unit) example using:
    https://merqube.com/index/MQEFAB01
    https://api.merqube.com/index?name=MQEFAB01
    """
    sid = "testid"

    ret = [
        {"eff_ts": "2023-04-03T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2061.3759657505516},
        {"eff_ts": "2023-04-04T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2058.4726656406847},
        {"eff_ts": "2023-04-05T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2052.2820122315807},
        {"eff_ts": "2023-04-06T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2060.1335590375693},
        {"eff_ts": "2023-04-10T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2060.2625642018947},
    ]

    gsm = pd.DataFrame.from_records(ret)

    def mock_get_collection(url, **kwargs):
        if url == "https://api.merqube.com/index?name=MQEFAB01":
            return [{"name": "MQEFAB01", "id": sid}]
        else:
            return [{"name": "index"}]  # get_security_metrics

    mock_secapi(
        monkeypatch,
        method_name_function_map={"get_security_metrics": MagicMock(return_value=gsm)},
        session_func_map={"get_collection": mock_get_collection},
        index_name="MQEFAB01",  # get_client_kwargs
    )

    client = get_client(index_name="MQEFAB01")

    df = client.get_returns(start_date=pd.Timestamp("2023-04-01"), end_date=pd.Timestamp("2023-04-10"))

    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert df.to_dict(orient="records") == ret
