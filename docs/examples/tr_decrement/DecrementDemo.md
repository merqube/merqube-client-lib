# TR + Decrement Index Demo

This document represents a full demo of creating a TR (single stock total return) index, and then a Decrement index overlay onto it.

NOTE: if you are only trying to create a decrement index on the universe of MerQube supplied TRs, jump to ##Creating the decrement.
This section only applies if you are also subscribed to create TR indices.

## Prequisites:

1. Must have an apikey with permission to create indices in some namespace
1. set `MERQ_API_KEY` to that key
1. Clone this repo and run `poetry install`

## Creating the TR

You can generate an example template with:

```fish
poetry run get_eb_template --index-type single_stock_total_return
```

which prints a json like this:

```json
{
    "base_date": "2000-01-04",
    "base_value": 1000.0,
    "bbg_ticker": "MY_TICKER",
    "currency": "USD",
    "description": "My Index Description",
    "email_list": [
        "bob@mycompany.com",
        "alice@mycompany.com"
    ],
    "is_intraday": false,
    "name": "My Index",
    "namespace": "mycompany",
    "reinvestment_type": "AT_OPEN",
    "ric": "LMVH.PA",
    "title": "My Index Title"
}
```

Fill out this template. Make sure to change `namespace` to the namespace your key is permissioned for.
Make sure to set the calendar correctly.

Parameters such as the index timezone, index holiday calendar, and daily index runtime are all determined on the server side based on the RIC.

Run the tool to create the index:

```fish
poetry run create --index-type=single_stock_total_return  --config-file-path ~/Desktop/single_stock_example.json --prod-run --poll 10
```

This will return the unique `uuid` of the index (you can use this on our API to access returns, or the name of the index).
The `poll` flag can be ommitted if you'd like, but we advise using it; if set it will poll the status of the index and inform about whether it was successful.

Note: you can just template the manifest without creating anything using:

```fish
poetry run create --index-type=single_stock_total_return  --config-file-path ~/Desktop/single_stock_example.json
```

## Accessing the TR

The above will launch an index titled `Demo_LVMH_TR_Index` (or, the value you used for `name`) into the namespace (`test` in this example).

After a few moments, (depending on how far back the `base_date` is), you will recieve the full historical Corporate Actions email for historical corporate actions since the `base_date`.

To access returns, you have three options:
1. You can use the daily emails (and the email that was sent upon creation with the historical return)

![Alt text](imgs/tr_returns_email.png?raw=true "Title")

2. You can navigate to the website at `https://merqube.com/index/Demo_LVMH_TR_Index`, replacing with your index name

![Alt text](imgs/tr_website.png?raw=true "Title")

3. You can use the API directly:

     curl -H "Authorization: APIKEY YOUR_API_KEY "https://api.merqube.com/security/index?name={name}&metrics=price_return" | jq .

4. You can use this client library to fetch returns, portfolios, etc:

```python
from merqube_client_lib.api_client.merqube_client import MerqubeAPIClientSingleIndex
from merqube_client_lib.util import get_token

client = MerqubeAPIClientSingleIndex(index_name="Demo_LVMH_TR_Index", token=get_token())
df = client.get_metrics(metrics=["price_return"])
print(df)  # a pandas dataframe
ports: list[dict[str, Any]] = client.get_portfolio()
```


which produces a dataframe:

```python
                   eff_ts                                    id                name  price_return
0     2000-01-04T00:00:00  8e677feb-0488-4b00-82a5-d8936f7dfbba  Demo_LVMH_TR_Index   1000.000000
1     2000-01-05T00:00:00  8e677feb-0488-4b00-82a5-d8936f7dfbba  Demo_LVMH_TR_Index    966.169154
2     2000-01-06T00:00:00  8e677feb-0488-4b00-82a5-d8936f7dfbba  Demo_LVMH_TR_Index    955.223881
3     2000-01-07T00:00:00  8e677feb-0488-4b00-82a5-d8936f7dfbba  Demo_LVMH_TR_Index    955.223881
4     2000-01-10T00:00:00  8e677feb-0488-4b00-82a5-d8936f7dfbba  Demo_LVMH_TR_Index    995.522388
...                   ...                                   ...                 ...           ...
5889  2023-06-01T00:00:00  8e677feb-0488-4b00-82a5-d8936f7dfbba  Demo_LVMH_TR_Index  16966.256715
5890  2023-06-02T00:00:00  8e677feb-0488-4b00-82a5-d8936f7dfbba  Demo_LVMH_TR_Index  17494.741505
5891  2023-06-05T00:00:00  8e677feb-0488-4b00-82a5-d8936f7dfbba  Demo_LVMH_TR_Index  17138.909117
5892  2023-06-06T00:00:00  8e677feb-0488-4b00-82a5-d8936f7dfbba  Demo_LVMH_TR_Index  17103.115326
5893  2023-06-07T00:00:00  8e677feb-0488-4b00-82a5-d8936f7dfbba  Demo_LVMH_TR_Index  17111.537395
```

## Creating the decrement

You can generate an example template for a decrement index with:

    poetry run get_eb_template --index-type decrement

which prints a json like this:

```json
{
    "base_date": "2000-01-04",
    "base_value": 1000.0,
    "bbg_ticker": "MY_TICKER",
    "currency": "USD",
    "day_count_convention": "f360",
    "description": "My Index Description",
    "email_list": [
        "bob@mycompany.com",
        "alice@mycompany.com"
    ],
    "fee_type": "fixed",
    "fee_value": 0.05,
    "is_intraday": false,
    "name": "My Index",
    "namespace": "mycompany",
    "ric": "LMVH.PA",
    "start_date": "2004-01-04",
    "title": "My Index Title"
}
```
(Note: decrements on general indices are not currently supported, but may be in the future. This is a single stock decrement)

In the backround, the library searches for a TR index with the same RIC.
It will raise an error if one (with that RIC) does not exist, or if there are no returns on or before the decrement `base_date`.

The same calendar as the underlying TR will be automatically applied.
Parameters such as the index timezone and daily index runtime are all determined on the server side based on the RIC.

Run the tool to create the index:

```fish
poetry run create --index-type=decrement --config-file-path ~/Desktop/decrement.json --prod-run --poll 10
```

## Accessing the decrement

Exactly like the above, you can either:
1. You can use the daily emails
1. Visit the website at
1. Use the API directly (the metric for this index is `total_return`)
1. You can use this client library:

```python
from merqube_client_lib.api_client.merqube_client import MerqubeAPIClientSingleIndex
from merqube_client_lib.util import get_token

client = MerqubeAPIClientSingleIndex(index_name="Demo_LVMH_Decrement_Index", token=get_token())
df = client.get_metrics(metrics=["price_return"])
print(df)  # a pandas dataframe
ports = client.get_portfolio()
```
gets your levels as a pandas dataframe:

```python
                   eff_ts  ... total_return
0     2000-01-04T00:00:00  ...  1000.000000
1     2000-01-05T00:00:00  ...   966.030265
2     2000-01-06T00:00:00  ...   954.947676
3     2000-01-07T00:00:00  ...   954.808787
4     2000-01-10T00:00:00  ...   994.673116
...                   ...  ...          ...
5889  2023-06-01T00:00:00  ...  2561.653239
5890  2023-06-02T00:00:00  ...  2641.307719
5891  2023-06-05T00:00:00  ...  2587.168461
5892  2023-06-06T00:00:00  ...  2581.626395
5893  2023-06-07T00:00:00  ...  2582.758774
```

## Together

You can also use the client library to compare both the TR and the decrement!

```python
import numpy as np

from merqube_client_lib.api_client.merqube_client import MerqubeAPIClient
from merqube_client_lib.util import get_token

client = MerqubeAPIClient(token=get_token())
df = client.get_security_metrics(
    sec_type="index",
    sec_names=["Demo_LVMH_TR_Index", "Demo_LVMH_Decrement_Index_4"],
    metrics=["price_return", "total_return"],
)

# Create the new DataFrame
# the 1.0 is an artifact of the TR index
df = df[["eff_ts", "name", "price_return", "total_return"]].mask(df == 1.0, np.nan)
df["level"] = df["price_return"].fillna(df["total_return"])
df = df.pivot(index="eff_ts", columns="name", values="level").rename(
    columns={"Demo_LVMH_TR_Index": "TR", "Demo_LVMH_Decrement_Index_4": "Decrement"}
)
print(df)
```

shows how the two levels diverge:

```python
                       Decrement            TR
eff_ts
2000-01-04T00:00:00  1000.000000   1000.000000
2000-01-05T00:00:00   966.030265    966.169154
2000-01-06T00:00:00   954.947676    955.223881
2000-01-07T00:00:00   954.808787    955.223881
2000-01-10T00:00:00   994.673116    995.522388
...                          ...           ...
2023-06-02T00:00:00  2641.307719  17494.741505
2023-06-05T00:00:00  2587.168461  17138.909117
2023-06-06T00:00:00  2581.626395  17103.115326
2023-06-07T00:00:00  2582.758774  17111.537395
2023-06-08T00:00:00  2582.619885  17111.537395
```
