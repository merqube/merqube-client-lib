"""
Integration tests for the API client class

These all use a "public" session with no token, to read public data ("default" namespace securities)
"""

from functools import partial

import pandas as pd
import pytest

from merqube_client_lib.api_client.merqube_client import get_client
from tests.unit.fixtures.gsm_fixtures import (
    mult_mult_assertion,
    mult_sing_assertion,
    sing_mult_assertion,
    sing_sing_assertion,
)


@pytest.mark.parametrize("should_raise", [True, False])
def test_permission_raise(should_raise):
    """Test that a permission error is raised when trying to access a private namespace if the flag is set"""
    public = get_client()

    if should_raise:
        with pytest.raises(PermissionError):
            public.get_security_metrics(sec_type="index", metrics=["price_return"])
        with pytest.raises(PermissionError):
            public.get_security_definitions_mapping_table(sec_type="index")

    else:
        public.get_security_metrics(sec_type="index", metrics=["price_return"])
        public.get_security_definitions_mapping_table(sec_type="index")


def test_mapping_table():
    """
    Test the mapping table for the security definitions
    """
    public = get_client()
    all_public_indices = public.get_security_definitions_mapping_table(sec_type="index")

    for k, v in {
        "NWSALTVI": "2963d69a-2c81-4ee5-9c0e-98fc1e476f2a",
        "MQEFAB01": "d84bc0d3-7788-4fed-9283-049eadab8964",
        "MQUSTRAV": "27514b7a-3575-4da1-a1f1-c22d0e361c78",
    }.items():
        assert all_public_indices[k] == v


def test_mapping_table_for_specific_names():
    public = get_client()
    mt = public.get_security_definitions_mapping_table(sec_type="index", sec_names=["NWSALTVI", "MQEFAB01"])
    assert mt["NWSALTVI"] == "2963d69a-2c81-4ee5-9c0e-98fc1e476f2a"
    assert mt["MQEFAB01"] == "d84bc0d3-7788-4fed-9283-049eadab8964"


def test_mapping_table_for_specific_ids():
    public = get_client()
    mt = public.get_security_definitions_mapping_table(
        sec_type="index", sec_ids=["2963d69a-2c81-4ee5-9c0e-98fc1e476f2a", "d84bc0d3-7788-4fed-9283-049eadab8964"]
    )
    assert mt["2963d69a-2c81-4ee5-9c0e-98fc1e476f2a"] == "NWSALTVI"
    assert mt["d84bc0d3-7788-4fed-9283-049eadab8964"] == "MQEFAB01"


def test_get_metric_defs_for_security():
    public = get_client()

    res_id = public.get_metrics_for_security(sec_type="index", sec_id="2963d69a-2c81-4ee5-9c0e-98fc1e476f2a")
    res_name = public.get_metrics_for_security(sec_type="index", sec_name="NWSALTVI")

    assert res_id == res_name  # same results by querying by id or name

    assert {
        "data_type": "float64",
        "description": "Index value reflecting only the price performance of " "constituents.",
        "name": "price_return",
    } in res_id


def gsm_call():
    public = get_client()

    sm = partial(
        public.get_security_metrics,
        sec_type="index",
        start_date=pd.Timestamp("2023-04-27"),
        end_date=pd.Timestamp("2023-05-03"),
        addl_options={"as_of": "2023-05-04T12:00:00"},  # result set is frozen
    )

    return sm


@pytest.mark.parametrize(
    "assertion",
    [
        sing_sing_assertion,
        sing_mult_assertion,
        mult_sing_assertion,
        mult_mult_assertion,
    ],
)
def test_get_security_metrics_no_chunks(assertion):
    """
    the assertion functions are imported becuase they are used in the unit tests (these arent mocked)
    """
    assertion(gsm_call())
