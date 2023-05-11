"""
Unit tests for indexapi
There are more in the integration tests
"""
import pytest

from merqube_client_lib.api_client.merqube_client import get_client

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
