"""
Integration tests for Indexapi
"""

import pytest

from merqube_client_lib.api_client.merqube_client import get_client


def test_prod_indices():
    """
    Test to get all public indices
    """
    client = get_client()
    prod_indices = client.get_index_defs()
    assert len(prod_indices) > 0
    for i in prod_indices.values():
        assert i["namespace"] == "default"
        assert i["stage"] == "prod", i["stage"]

    all_indices = client.get_index_defs(include_nonprod=False)
    assert len(all_indices) >= len(prod_indices)
    for i in all_indices.values():
        assert i["namespace"] == "default"


@pytest.mark.parametrize("names", [("asdfasdfasfd"), (["asdfasf"]), (["asfdasfd", "asfsasdf"]), ("asdfasf,asfdasfd")])
def test_empty_results(names):
    """
    Test to get empty results
    """
    client = get_client()
    prod_indices = client.get_index_defs(names)
    assert len(prod_indices) == 0


REAL_PUBLIC_NAMES = ["NWSALTVI", "MQUSTRAV"]


@pytest.mark.parametrize(
    "names, expected",
    [
        ("NWSALTVI", 1),
        (["NWSALTVI"], 1),
        (["NWSALTVI", "MQUSTRAV"], 2),
        ("NWSALTVI,MQUSTRAV", 2),
        # we include garbage names in these queries; they dont affect the results
        ("NWSALTVI,asdfasdfasdf", 1),
        (["NWSALTVI", "asdfasdfasdf"], 1),
        (["NWSALTVI", "MQUSTRAV", "asdfasdfasdf"], 2),
        ("NWSALTVI,MQUSTRAV,asdfasdfasdf", 2),
    ],
)
def test_results(names, expected):
    """
    Test to get results for ?names=queries
    """
    client = get_client()
    prod_indices = client.get_index_defs(names)
    assert len(prod_indices) == expected

    for i in prod_indices.values():
        assert i["namespace"] == "default"
