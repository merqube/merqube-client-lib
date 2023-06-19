"""
NOTE: in circle CI there is a MERQ_API_KEY set to a test key which has index create access on the test namespace
You will not be able to run this particular test locally unless you set that ENV to that key locally - but 
you can run the test in circle ci
"""
import random
import string
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
from merqube_client_lib.pydantic_types import (
    Administrative,
    AssetType,
    BasketPosition,
    EquityBasketPortfolio,
    IdentifierType,
    IndexDefinitionPost,
    MerqTimestamp,
    PortfolioUom,
    RicEquityPosition,
    Role,
)
from merqube_client_lib.types import TargetPortfoliosDates
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

tp = cast(
    TargetPortfoliosDates,
    [
        (
            pd.Timestamp("2023-06-12 00:00:00"),
            EquityBasketPortfolio(
                positions=[
                    RicEquityPosition(
                        amount=15.0,
                        asset_type=AssetType.EQUITY,
                        identifier="AA.N",
                        identifier_type=IdentifierType.RIC,
                        position_id=None,
                        real_time_trade_types=None,
                        use_primary_listing=False,
                    ),
                ],
                timestamp=MerqTimestamp(__root__=pd.Timestamp("2023-06-12 00:00:00")),
                unit_of_measure=PortfolioUom.SHARES,
            ),
        ),  # this portfolio will be overshadowed by the second, since it has the same eff_ts. so, we will post it,
        # but it will not be returned by the get_target_portfolio call
        (
            pd.Timestamp("2023-06-12 00:00:00"),
            EquityBasketPortfolio(
                positions=[
                    RicEquityPosition(
                        amount=1.0,
                        asset_type=AssetType.EQUITY,
                        identifier="AA.N",
                        identifier_type=IdentifierType.RIC,
                        position_id=None,
                        real_time_trade_types=None,
                        use_primary_listing=False,
                    ),
                    RicEquityPosition(
                        amount=2.0,
                        asset_type=AssetType.EQUITY,
                        identifier="AAPL.OQ",
                        identifier_type=IdentifierType.RIC,
                        position_id=None,
                        real_time_trade_types=None,
                        use_primary_listing=False,
                    ),
                ],
                timestamp=MerqTimestamp(__root__=pd.Timestamp("2023-06-12 00:00:00")),
                unit_of_measure=PortfolioUom.SHARES,
            ),
        ),
        (
            pd.Timestamp("2023-06-13 00:00:00"),
            EquityBasketPortfolio(
                positions=[
                    RicEquityPosition(
                        amount=2.0,
                        asset_type=AssetType.EQUITY,
                        identifier="AA.N",
                        identifier_type=IdentifierType.RIC,
                        position_id=None,
                        real_time_trade_types=None,
                        use_primary_listing=False,
                    ),
                    BasketPosition(
                        amount=100000000.0,
                        asset_type=AssetType.CASH,
                        identifier="USD",
                        identifier_type=IdentifierType.CURRENCY_CODE,
                        position_id=None,
                    ),
                ],
                timestamp=MerqTimestamp(__root__=pd.Timestamp("2023-06-13 00:00:00")),
                unit_of_measure=PortfolioUom.SHARES,
            ),
        ),
    ],
)

# the 1: is in reference to the comment above about the first portfolio for the 12th being overshadowed by the second on the client side
expected = sorted([pydantic_to_dict(x) for x in [y[1] for y in tp[1:]]], key=lambda x: x["timestamp"])
for e in expected:
    e["eff_ts"] = e["timestamp"]
    e["target_portfolio"] = {
        "positions": e["positions"],
        "timestamp": e["timestamp"],
        "unit_of_measure": e["unit_of_measure"],
    }
    for k in ["positions", "timestamp", "unit_of_measure"]:
        del e[k]


def test_index_workflow():
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

        for tpd in tp:
            sing_cl.replace_portfolio(target_portfolio=tpd[1])

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