"""
fixtures shared between unit and integration tests

    sample of public securities
    ---------------------------
    MQ2S0B04 -> ID1
    MQ2Q0BQR -> ID2
    MQ2S0B01 -> ID3

    sample of metrics:
    -----------------
    daily_return
    price_return
    total_return
"""

import pandas as pd

ID1 = "6a083435-9118-48ef-a7a9-a7633cdc0a9c"
ID2 = "f056cf50-1f75-4fae-87d6-230e2d676975"
ID3 = "ee56deaf-c012-421e-91a6-099649e12738"

TEST_IDS = [ID1, ID2, ID3]
N1 = "MQ2S0B04"
N2 = "MQ2Q0BQR"
N3 = "MQ2S0B01"

TEST_NAMES = [N1, N2, N3]

TEST_METRICS = ["daily_return", "price_return", "total_return"]

# For testing with adding in non existing securities and metrics
TEST_IDS_NE = TEST_IDS + ["doesnotexist"]
TEST_METRICS_NE = TEST_METRICS + ["metricdoesnotexist"]
TEST_NAMES_NE = TEST_NAMES + ["doesnotexist"]


SING_SING_EXPECTED = [
    {"eff_ts": "2023-04-27T00:00:00", "id": ID1, "name": "MQ2S0B04", "price_return": 5170.548754663037},
    {"eff_ts": "2023-04-28T00:00:00", "id": ID1, "name": "MQ2S0B04", "price_return": 5204.776415405893},
    {"eff_ts": "2023-05-01T00:00:00", "id": ID1, "name": "MQ2S0B04", "price_return": 5208.520982353278},
    {"eff_ts": "2023-05-02T00:00:00", "id": ID1, "name": "MQ2S0B04", "price_return": 5166.300254047452},
    {"eff_ts": "2023-05-03T00:00:00", "id": ID1, "name": "MQ2S0B04", "price_return": 5135.063369405323},
]

SING_MULT_EXPECTED = [
    {
        "daily_return": 0.015768430297548486,
        "eff_ts": "2023-04-27T00:00:00",
        "id": ID1,
        "name": "MQ2S0B04",
        "price_return": 5170.548754663037,
        "total_return": 5170.548754662921,
    },
    {
        "daily_return": 0.0066197346484719866,
        "eff_ts": "2023-04-28T00:00:00",
        "id": ID1,
        "name": "MQ2S0B04",
        "price_return": 5204.776415405893,
        "total_return": 5204.776415405777,
    },
    {
        "daily_return": 0.0007194481853822765,
        "eff_ts": "2023-05-01T00:00:00",
        "id": ID1,
        "name": "MQ2S0B04",
        "price_return": 5208.520982353278,
        "total_return": 5208.520982353161,
    },
    {
        "daily_return": -0.008106087783628424,
        "eff_ts": "2023-05-02T00:00:00",
        "id": ID1,
        "name": "MQ2S0B04",
        "price_return": 5166.300254047452,
        "total_return": 5166.300254047336,
    },
    {
        "daily_return": -0.006046277433770286,
        "eff_ts": "2023-05-03T00:00:00",
        "id": ID1,
        "name": "MQ2S0B04",
        "price_return": 5135.063369405323,
        "total_return": 5135.0633694052085,
    },
]

MULT_SING_EXPECTED = [
    {"eff_ts": "2023-04-27T00:00:00", "id": ID1, "name": "MQ2S0B04", "price_return": 5170.548754663037},
    {"eff_ts": "2023-04-28T00:00:00", "id": ID1, "name": "MQ2S0B04", "price_return": 5204.776415405893},
    {"eff_ts": "2023-05-01T00:00:00", "id": ID1, "name": "MQ2S0B04", "price_return": 5208.520982353278},
    {"eff_ts": "2023-05-02T00:00:00", "id": ID1, "name": "MQ2S0B04", "price_return": 5166.300254047452},
    {"eff_ts": "2023-05-03T00:00:00", "id": ID1, "name": "MQ2S0B04", "price_return": 5135.063369405323},
    {"eff_ts": "2023-04-27T00:00:00", "id": ID2, "name": "MQ2Q0BQR", "price_return": 7513.1327368801985},
    {"eff_ts": "2023-04-28T00:00:00", "id": ID2, "name": "MQ2Q0BQR", "price_return": 7570.85166736415},
    {"eff_ts": "2023-05-01T00:00:00", "id": ID2, "name": "MQ2Q0BQR", "price_return": 7566.061141214855},
    {"eff_ts": "2023-05-02T00:00:00", "id": ID2, "name": "MQ2Q0BQR", "price_return": 7504.435990625394},
    {"eff_ts": "2023-05-03T00:00:00", "id": ID2, "name": "MQ2Q0BQR", "price_return": 7451.6931008917645},
    {"eff_ts": "2023-04-27T00:00:00", "id": ID3, "name": "MQ2S0B01", "price_return": 4689.62311691927},
    {"eff_ts": "2023-04-28T00:00:00", "id": ID3, "name": "MQ2S0B01", "price_return": 4718.632382133441},
    {"eff_ts": "2023-05-01T00:00:00", "id": ID3, "name": "MQ2S0B01", "price_return": 4712.435103936917},
    {"eff_ts": "2023-05-02T00:00:00", "id": ID3, "name": "MQ2S0B01", "price_return": 4680.6114763316355},
    {"eff_ts": "2023-05-03T00:00:00", "id": ID3, "name": "MQ2S0B01", "price_return": 4657.584331839027},
]


MULT_MULT_EXPECTED = [
    {
        "daily_return": 0.015768430297548486,
        "eff_ts": "2023-04-27T00:00:00",
        "id": ID1,
        "name": "MQ2S0B04",
        "price_return": 5170.548754663037,
        "total_return": 5170.548754662921,
    },
    {
        "daily_return": 0.0066197346484719866,
        "eff_ts": "2023-04-28T00:00:00",
        "id": ID1,
        "name": "MQ2S0B04",
        "price_return": 5204.776415405893,
        "total_return": 5204.776415405777,
    },
    {
        "daily_return": 0.0007194481853822765,
        "eff_ts": "2023-05-01T00:00:00",
        "id": ID1,
        "name": "MQ2S0B04",
        "price_return": 5208.520982353278,
        "total_return": 5208.520982353161,
    },
    {
        "daily_return": -0.008106087783628424,
        "eff_ts": "2023-05-02T00:00:00",
        "id": ID1,
        "name": "MQ2S0B04",
        "price_return": 5166.300254047452,
        "total_return": 5166.300254047336,
    },
    {
        "daily_return": -0.006046277433770286,
        "eff_ts": "2023-05-03T00:00:00",
        "id": ID1,
        "name": "MQ2S0B04",
        "price_return": 5135.063369405323,
        "total_return": 5135.0633694052085,
    },
    {
        "daily_return": 0.027810815383743748,
        "eff_ts": "2023-04-27T00:00:00",
        "id": ID2,
        "name": "MQ2Q0BQR",
        "price_return": 7513.1327368801985,
        "total_return": 7513.132736880319,
    },
    {
        "daily_return": 0.007682405263602199,
        "eff_ts": "2023-04-28T00:00:00",
        "id": ID2,
        "name": "MQ2Q0BQR",
        "price_return": 7570.85166736415,
        "total_return": 7570.85166736427,
    },
    {
        "daily_return": -0.0006327592138604121,
        "eff_ts": "2023-05-01T00:00:00",
        "id": ID2,
        "name": "MQ2Q0BQR",
        "price_return": 7566.061141214855,
        "total_return": 7566.061141214975,
    },
    {
        "daily_return": -0.008144944831831702,
        "eff_ts": "2023-05-02T00:00:00",
        "id": ID2,
        "name": "MQ2Q0BQR",
        "price_return": 7504.435990625394,
        "total_return": 7504.435990625513,
    },
    {
        "daily_return": -0.007028228343811116,
        "eff_ts": "2023-05-03T00:00:00",
        "id": ID2,
        "name": "MQ2Q0BQR",
        "price_return": 7451.6931008917645,
        "total_return": 7451.693100891883,
    },
    {
        "daily_return": 0.015056431367249212,
        "eff_ts": "2023-04-27T00:00:00",
        "id": ID3,
        "name": "MQ2S0B01",
        "price_return": 4689.62311691927,
        "total_return": 4689.62311691938,
    },
    {
        "daily_return": 0.006185841482551302,
        "eff_ts": "2023-04-28T00:00:00",
        "id": ID3,
        "name": "MQ2S0B01",
        "price_return": 4718.632382133441,
        "total_return": 4718.632382133551,
    },
    {
        "daily_return": -0.0013133632151530739,
        "eff_ts": "2023-05-01T00:00:00",
        "id": ID3,
        "name": "MQ2S0B01",
        "price_return": 4712.435103936917,
        "total_return": 4712.435103937027,
    },
    {
        "daily_return": -0.0067531174230271995,
        "eff_ts": "2023-05-02T00:00:00",
        "id": ID3,
        "name": "MQ2S0B01",
        "price_return": 4680.6114763316355,
        "total_return": 4680.611476331745,
    },
    {
        "daily_return": -0.004919687226561997,
        "eff_ts": "2023-05-03T00:00:00",
        "id": ID3,
        "name": "MQ2S0B01",
        "price_return": 4657.584331839027,
        "total_return": 4657.584331839136,
    },
]


def sing_sing_assertion(sm):
    # single single with df_labels set to nothing then both possible options:
    single_single = sm(sec_ids=ID1, metrics="price_return")
    assert single_single.columns.tolist() == [
        "eff_ts",
        "id",
        "name",
        "price_return",
    ]
    assert len(single_single) == 5  # unique row for all cols != id,name in this case.
    assert single_single.index.equals(pd.RangeIndex(start=0, stop=5, step=1))

    assert single_single.to_dict(orient="records") == SING_SING_EXPECTED

    # Querying by name is same result
    single_single_name = sm(sec_names=N1, metrics="price_return")
    assert single_single_name.to_dict(orient="records") == SING_SING_EXPECTED


def sing_mult_assertion(sm):
    single_mult = sm(sec_ids=ID1, metrics=TEST_METRICS)

    assert single_mult.columns.tolist() == ["daily_return", "eff_ts", "id", "name", "price_return", "total_return"]
    assert len(single_mult) == 5
    assert single_mult.index.equals(pd.RangeIndex(start=0, stop=5, step=1))
    assert single_mult.to_dict(orient="records") == SING_MULT_EXPECTED

    single_mult_name = sm(sec_names=N1, metrics=TEST_METRICS)
    assert single_mult_name.to_dict(orient="records") == SING_MULT_EXPECTED


def mult_sing_assertion(sm):
    mult_single = sm(sec_ids=TEST_IDS, metrics="price_return")

    assert len(mult_single) == 15  # 5x3
    assert mult_single.columns.tolist() == ["eff_ts", "id", "name", "price_return"]
    assert mult_single.index.equals(pd.RangeIndex(start=0, stop=15, step=1))

    assert mult_single.to_dict(orient="records") == MULT_SING_EXPECTED
    mult_single_name = sm(sec_names=TEST_NAMES, metrics="price_return")
    assert mult_single_name.to_dict(orient="records") == MULT_SING_EXPECTED


def mult_mult_assertion(sm):  # multu mult
    mult_mult = sm(
        sec_ids=TEST_IDS,
        metrics=TEST_METRICS,
    )

    assert len(mult_mult) == 15  # 5x3 but more records per entry
    assert mult_mult.columns.tolist() == ["daily_return", "eff_ts", "id", "name", "price_return", "total_return"]

    assert mult_mult.to_dict(orient="records") == MULT_MULT_EXPECTED

    mult_mult_name = sm(sec_names=TEST_NAMES, metrics=TEST_METRICS)
    assert mult_mult_name.to_dict(orient="records") == MULT_MULT_EXPECTED
