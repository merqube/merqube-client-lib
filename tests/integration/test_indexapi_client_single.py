import pytest
from pydantic import BaseModel

from merqube_client_lib.api_client.merqube_client import MerqubeAPIClientSingleIndex
from merqube_client_lib.exceptions import APIError
from merqube_client_lib.session import get_public_merqube_session


def test_nonexistent():
    with pytest.raises(APIError):
        MerqubeAPIClientSingleIndex(index_name="thisdoesnotexist", user_session=get_public_merqube_session())


def test_single():
    """
    Full example using:
    https://merqube.com/index/MQEFAB01
    https://api.merqube.com/index?name=MQEFAB01
    """
    client = MerqubeAPIClientSingleIndex(index_name="MQEFAB01", user_session=get_public_merqube_session())

    assert isinstance(client.get_index_manifest(), dict)

    assert isinstance(client.get_index_model(), BaseModel)

    # these are frozen and never change, unless there is a (rare) historical correction
    port = client.get_portfolio()
    assert port[0]["date"] == "2006-12-29T00:00:00"
    assert "OPTION:EFA:CALL:0.0:2007-12-31:BUY" in port[0]["portfolio"]

    port_alloc = client.get_portfolio_allocations()
    assert port_alloc[0]["portfolio"]["OPTION:EFA:CALL:0.0:2007-12-31:BUY"] == 0.9665825874209992

    caps = client.get_caps()
    assert {
        "cap": {"EFA": 7.1526071526072155, "cap": None, "performance": 7.30052164929349},
        "date": "2006-12-29T00:00:00",
        "id": "2006-12-29T00:00:00",
    } in caps

    # no value assertions here because these change every day
    stats = client.get_stats()
    for k in [
        "annual_volatility",
        "annualized_return",
        "cumulative_return",
        "end_date",
        "id",
        "max_drawdown",
        "sharpe_ratio",
        "start_date",
    ]:
        assert k in stats[0]

    # target portfolios and data collections are not available for this index
