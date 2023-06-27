import pandas as pd
import pandas_market_calendars as mcal
import pytest
from pydantic import BaseModel

from merqube_client_lib.api_client.merqube_client import MerqubeAPIClientSingleIndex
from merqube_client_lib.exceptions import APIError
from merqube_client_lib.session import get_merqube_session


def test_nonexistent():
    with pytest.raises(APIError):
        MerqubeAPIClientSingleIndex(index_name="thisdoesnotexist", user_session=get_merqube_session())


def test_single_index_operations():
    """
    Full example using:
    https://merqube.com/index/MQEFAB01
    https://api.merqube.com/index?name=MQEFAB01
    """
    client = MerqubeAPIClientSingleIndex(index_name="MQEFAB01", user_session=get_merqube_session())

    assert isinstance(client.get_manifest(), dict)

    assert isinstance(client.get_model(), BaseModel)

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


def test_single_index_returns():
    """
    Full example using:
    https://merqube.com/index/MQEFAB01
    https://api.merqube.com/index?name=MQEFAB01
    """
    client = MerqubeAPIClientSingleIndex(index_name="MQEFAB01", user_session=get_merqube_session())
    df = client.get_returns(start_date=pd.Timestamp("2023-04-01"), end_date=pd.Timestamp("2023-05-01"))

    assert isinstance(df, pd.DataFrame)
    assert not df.empty

    sid = "d84bc0d3-7788-4fed-9283-049eadab8964"
    assert df.to_dict(orient="records") == [
        {"eff_ts": "2023-04-03T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2061.3759657505516},
        {"eff_ts": "2023-04-04T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2058.4726656406847},
        {"eff_ts": "2023-04-05T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2052.2820122315807},
        {"eff_ts": "2023-04-06T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2060.1335590375693},
        {"eff_ts": "2023-04-10T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2060.2625642018947},
        {"eff_ts": "2023-04-11T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2065.2562703626586},
        {"eff_ts": "2023-04-12T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2070.291345358123},
        {"eff_ts": "2023-04-13T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2092.4128224566343},
        {"eff_ts": "2023-04-14T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2088.767771842511},
        {"eff_ts": "2023-04-17T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2084.5264838309063},
        {"eff_ts": "2023-04-18T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2091.8147254568066},
        {"eff_ts": "2023-04-19T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2090.477285497472},
        {"eff_ts": "2023-04-20T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2085.844141746835},
        {"eff_ts": "2023-04-21T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2093.9443207973086},
        {"eff_ts": "2023-04-24T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2100.3887653420798},
        {"eff_ts": "2023-04-25T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2078.0373192902475},
        {"eff_ts": "2023-04-26T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2077.5464610492604},
        {"eff_ts": "2023-04-27T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2094.681756502886},
        {"eff_ts": "2023-04-28T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2084.1597797916966},
        {"eff_ts": "2023-05-01T00:00:00", "id": sid, "name": "MQEFAB01", "price_return": 2097.136207320045},
    ]


def test_single_intraday_index_return():
    """
    MQUSTRAV realtime ("intraday") index
    """
    client = MerqubeAPIClientSingleIndex(index_name="MQUSTRAV", is_intraday=True, user_session=get_merqube_session())

    # RT indices only store 5 second ticks for 7 business days
    # get the last trading day before today
    nyse = mcal.get_calendar("NYSE")
    today = pd.Timestamp.now(tz="America/New_York").date()
    # nyse should never have a block of 6 days off
    sched = nyse.schedule(start_date=today - pd.Timedelta(days=6), end_date=today)
    ltd = sched.index.to_list()[-2]

    # form a 1 minute trading window, the index ticks every 5 seconds
    start_date = pd.Timestamp(year=ltd.year, month=ltd.month, day=ltd.day, hour=19, minute=0, second=0)  # UTC time
    end_date = pd.Timestamp(year=ltd.year, month=ltd.month, day=ltd.day, hour=19, minute=1, second=0)

    """
    We dont assert a value since the window of data changes every night, we just assert nonempty. 
    Example of an actual df:

                     eff_ts                                    id      name  price_return
    0   2023-05-15T19:00:00  e0825ead-bb51-40c4-8130-76a1d44c368d  MQUSTRAV   1948.487644
    1   2023-05-15T19:00:05  e0825ead-bb51-40c4-8130-76a1d44c368d  MQUSTRAV   1948.295987
    2   2023-05-15T19:00:10  e0825ead-bb51-40c4-8130-76a1d44c368d  MQUSTRAV   1948.294829
    3   2023-05-15T19:00:15  e0825ead-bb51-40c4-8130-76a1d44c368d  MQUSTRAV   1948.363435
    4   2023-05-15T19:00:20  e0825ead-bb51-40c4-8130-76a1d44c368d  MQUSTRAV   1948.339992
    5   2023-05-15T19:00:25  e0825ead-bb51-40c4-8130-76a1d44c368d  MQUSTRAV   1948.339992
    6   2023-05-15T19:00:30  e0825ead-bb51-40c4-8130-76a1d44c368d  MQUSTRAV   1948.255751
    7   2023-05-15T19:00:35  e0825ead-bb51-40c4-8130-76a1d44c368d  MQUSTRAV   1948.268566
    8   2023-05-15T19:00:40  e0825ead-bb51-40c4-8130-76a1d44c368d  MQUSTRAV   1948.266249
    9   2023-05-15T19:00:45  e0825ead-bb51-40c4-8130-76a1d44c368d  MQUSTRAV   1948.253435
    10  2023-05-15T19:00:50  e0825ead-bb51-40c4-8130-76a1d44c368d  MQUSTRAV   1948.197780
    11  2023-05-15T19:00:55  e0825ead-bb51-40c4-8130-76a1d44c368d  MQUSTRAV   1948.192617
    12  2023-05-15T19:01:00  e0825ead-bb51-40c4-8130-76a1d44c368d  MQUSTRAV   1948.227063
    """

    df = client.get_returns(start_date=start_date, end_date=end_date, use_intraday_metrics=True)
    assert not df.empty
    assert len(df["price_return"].tolist()) > 2

    # EOD we can test a fixed window
    df = client.get_returns(
        start_date=pd.Timestamp("2023-05-12"), end_date=pd.Timestamp("2023-05-15"), use_intraday_metrics=False
    )
    assert df.to_dict(orient="records") == [
        {
            "eff_ts": "2023-05-12T00:00:00",
            "id": "27514b7a-3575-4da1-a1f1-c22d0e361c78",
            "name": "MQUSTRAV",
            "price_return": 1926.1529634388705,
        },
        {
            "eff_ts": "2023-05-15T00:00:00",
            "id": "27514b7a-3575-4da1-a1f1-c22d0e361c78",
            "name": "MQUSTRAV",
            "price_return": 1950.7413459671484,
        },
    ]


def test_single_index_multiple_metrics():
    """
    Full example using:
    https://merqube.com/index/MQ2Q0BQR
    https://api.merqube.com/index?name=MQ2Q0BQR
    """
    client = MerqubeAPIClientSingleIndex(index_name="MQ2Q0BQR", user_session=get_merqube_session())

    mets = ["price_return", "daily_return", "net_total_return", "total_return"]

    df = client.get_metrics(metrics=mets, start_date=pd.Timestamp("2023-04-01"), end_date=pd.Timestamp("2023-04-10"))

    assert isinstance(df, pd.DataFrame)
    assert not df.empty

    sid = "f056cf50-1f75-4fae-87d6-230e2d676975"
    assert df.to_dict(orient="records") == [
        {
            "daily_return": -0.001490379831880495,
            "eff_ts": "2023-04-03T00:00:00",
            "id": sid,
            "name": "MQ2Q0BQR",
            "net_total_return": 7435.441291840737,
            "price_return": 7435.441291840617,
            "total_return": 7435.441291840737,
        },
        {
            "daily_return": -0.0023339663506358743,
            "eff_ts": "2023-04-04T00:00:00",
            "id": sid,
            "name": "MQ2Q0BQR",
            "net_total_return": 7418.087222063452,
            "price_return": 7418.087222063333,
            "total_return": 7418.087222063452,
        },
        {
            "daily_return": -0.00802688787903727,
            "eff_ts": "2023-04-05T00:00:00",
            "id": sid,
            "name": "MQ2Q0BQR",
            "net_total_return": 7358.5430676550295,
            "price_return": 7358.543067654911,
            "total_return": 7358.5430676550295,
        },
        {
            "daily_return": 0.005579187693722787,
            "eff_ts": "2023-04-06T00:00:00",
            "id": sid,
            "name": "MQ2Q0BQR",
            "net_total_return": 7399.59776058182,
            "price_return": 7399.597760581701,
            "total_return": 7399.59776058182,
        },
        {
            "daily_return": 0.0009701824776102708,
            "eff_ts": "2023-04-10T00:00:00",
            "id": sid,
            "name": "MQ2Q0BQR",
            "net_total_return": 7406.7767206705,
            "price_return": 7406.776720670382,
            "total_return": 7406.7767206705,
        },
    ]
