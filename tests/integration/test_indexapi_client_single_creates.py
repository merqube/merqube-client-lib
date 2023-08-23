"""
NOTE: in circle CI there is a MERQ_API_KEY set to a test key which has index create access on the test namespace
You will not be able to run this particular test locally unless you set that ENV to that key locally
(but you can run the test in circle ci)
"""
import random
import string
import time
from typing import cast

import pandas as pd
import pytest

from merqube_client_lib.api_client import merqube_client
from merqube_client_lib.api_client.merqube_client import (
    MerqubeAPIClientSingleIndex,
    get_client,
)
from merqube_client_lib.constants import STAGING_API_URL
from merqube_client_lib.exceptions import APIError
from merqube_client_lib.logging import get_module_logger
from merqube_client_lib.pydantic_v2_types import (
    Administrative,
    AssetType,
    BasketPosition,
    EquityBasketPortfolio,
    EquityIdentifierType,
    IndexDefinitionPost,
    PortfolioUom,
    RicEquityPosition,
    Role,
)
from merqube_client_lib.util import get_token, pydantic_to_dict

logger = get_module_logger(__name__)

# note: this index has no run_configuration so nothing will run, but it will be created
TEST_IND = IndexDefinitionPost(
    administrative=Administrative(role=Role.development),
    description="Client lib int test",
    family="soprano",
    name="cl_int_test",
    namespace="test",
    stage="development",
    title="Client lib int test",
    launch_date="2066-06-06",
)

tp = [
    EquityBasketPortfolio(
        positions=[
            RicEquityPosition(
                amount=15.0,
                asset_type=AssetType.EQUITY,
                identifier="AA.N",
                identifier_type=EquityIdentifierType.RIC,
                position_id=None,
                real_time_trade_types=None,
                use_primary_listing=False,
            ),
        ],
        timestamp="2023-06-12T00:00:00",
        unit_of_measure=PortfolioUom.SHARES,
    ),  # this portfolio will be overshadowed by the second, since it has the same eff_ts. so, we will post it,
    # but it will not be returned by the get_target_portfolio call
    EquityBasketPortfolio(
        positions=[
            RicEquityPosition(
                amount=1.0,
                asset_type=AssetType.EQUITY,
                identifier="AA.N",
                identifier_type=EquityIdentifierType.RIC,
                position_id=None,
                real_time_trade_types=None,
                use_primary_listing=False,
            ),
            RicEquityPosition(
                amount=2.0,
                asset_type=AssetType.EQUITY,
                identifier="AAPL.OQ",
                identifier_type=EquityIdentifierType.RIC,
                position_id=None,
                real_time_trade_types=None,
                use_primary_listing=False,
            ),
        ],
        timestamp="2023-06-12T00:00:00",
        unit_of_measure=PortfolioUom.SHARES,
    ),
    EquityBasketPortfolio(
        positions=[
            RicEquityPosition(
                amount=2.0,
                asset_type=AssetType.EQUITY,
                identifier="AA.N",
                identifier_type=EquityIdentifierType.RIC,
                position_id=None,
                real_time_trade_types=None,
                use_primary_listing=False,
            ),
            BasketPosition(
                amount=100000000.0,
                asset_type=AssetType.CASH,
                identifier="USD",
                identifier_type=EquityIdentifierType.CURRENCY_CODE,
                position_id=None,
            ),
        ],
        timestamp="2023-06-13T00:00:00",
        unit_of_measure=PortfolioUom.SHARES,
    ),
]

# the 1: is in reference to the comment above about the first portfolio for the 12th being overshadowed by the second on the client side
expected = [pydantic_to_dict(x) for x in tp[1:]]
for e in expected:
    e["eff_ts"] = e["timestamp"]
    e["target_portfolio"] = {
        "positions": e["positions"],
        "timestamp": e["timestamp"],
        "unit_of_measure": e["unit_of_measure"],
    }
    for k in ["positions", "timestamp", "unit_of_measure"]:
        del e[k]


def _test_target_ports(sing_cl):
    sing_cl.replace_portfolio(tp)

    assert sing_cl.get_target_portfolio() == expected
    # start date before both
    assert sing_cl.get_target_portfolio(start_date=pd.Timestamp("2023-06-12 00:00:00")) == expected
    # end date after both
    assert sing_cl.get_target_portfolio(end_date=pd.Timestamp("2023-06-15 00:00:00")) == expected
    # start date on second
    assert sing_cl.get_target_portfolio(start_date=pd.Timestamp("2023-06-13 00:00:00")) == expected[1:]
    # end date on first
    assert sing_cl.get_target_portfolio(end_date=pd.Timestamp("2023-06-12 00:00:00")) == expected[:1]
    # start date after both
    assert sing_cl.get_target_portfolio(start_date=pd.Timestamp("2023-06-15 00:00:00")) == []
    # end date before both
    assert sing_cl.get_target_portfolio(end_date=pd.Timestamp("2023-06-11 00:00:00")) == []


def test_index_workflow():
    """
    creates an index
    runs through a bunch of index functionality
    deletes the index
    """
    cl = get_client(token=get_token(), prefix_url=STAGING_API_URL)

    test_name = "cl_int_test" + "".join(random.choice(string.digits) for i in range(10))
    TEST_IND.name = test_name
    logger.info(f"Creating index: {test_name}")

    res = cl.create_index(index_def=TEST_IND)
    newid = res["id"]

    try:
        sing_cl = cast(
            MerqubeAPIClientSingleIndex, get_client(token=get_token(), prefix_url=STAGING_API_URL, index_name=test_name)
        )

        # change the description:
        assert sing_cl.get_manifest()["description"] == "Client lib int test"
        sing_cl.partial_update(updates={"description": "new description"})
        assert sing_cl.get_manifest()["description"] == "new description"

        # lock the index
        sing_cl.lock()
        assert sing_cl.get_manifest()["status"]["locked_after"] is not None

        time.sleep(5)  # clock skew

        # try to update the description, which should fail
        with pytest.raises(APIError) as e:
            res = sing_cl.partial_update(updates={"description": "new description 2"})

        assert e.value.code == 400
        assert e.value.response_json["error"].startswith(
            "This manifest is locked. You must unlock it before making any changes. Locked since:"
        )

        # unlock the index (so it can be deleted later)
        sing_cl.unlock()
        assert sing_cl.get_manifest()["status"].get("locked_after") is None

        # try again:
        assert sing_cl.get_manifest()["description"] == "new description"
        sing_cl.partial_update(updates={"description": "new description 2"})
        assert sing_cl.get_manifest()["description"] == "new description 2"

        # test TP functionality
        _test_target_ports(sing_cl)

    finally:
        cl.delete_index(index_id=newid)
        # clear the cache so we dont get the same object back (which is now broken)
        merqube_client.client_cache.clear()

        # can no longer make a single index class
        with pytest.raises(APIError):
            get_client(token=get_token(), prefix_url=STAGING_API_URL, index_name=test_name)

        # multi client will find no results
        with pytest.raises(APIError):
            assert cl.get_index_manifest(index_name=test_name) == []
