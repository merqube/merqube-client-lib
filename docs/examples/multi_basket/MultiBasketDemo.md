# Equity Basket Demo

This document represents a full demo of creating a basket of equities as an index, and then requesting rebalances on specific days.

The client can choose to

## Prequisites:

1. Must have an apikey with permission to create indices in some namespace
1. set `MERQ_API_KEY` to that key
1. Clone this repo and run `poetry install`

## Creating the Index

You can generate an example template with:

```fish
poetry run get_eb_template --index-type multiple_equity_basket"
```

which prints a json like:

```json
{
    "base_date": "2000-01-04",
    "base_value": 1000.0,
    "bbg_ticker": "MY_TICKER",
    "constituents_csv_path": "/path/to/constituents.csv",
    "corporate_actions": {
        "reinvest_dividends": true
    },
    "currency": "USD",
    "description": "My Index Description",
    "email_list": [
        "bob@mycompany.com",
        "alice@mycompany.com"
    ],
    "holiday_calendar": null,
    "is_intraday": false,
    "level_overrides_csv_path": "/path/to/overrides.csv",
    "name": "My Index",
    "namespace": "mycompany",
    "run_hour": 16,
    "run_minute": 30,
    "timezone": "US/Eastern",
    "title": "My Index Title"
}
```

Make sure to change `namespace` to the namespace your key is permissioned for.

The `constituents_csv_path` is a CSV containing the initial portfolio.
There is another script (discussed below) for updating an existing index with a new portfolio (e.g., a rebalance).
The index will start computing given the initial portfolio, and will self adjust over time according to corporate actions, until a new explicit portfolio is given using the update tool.
In the extreme case, uploading a new portfolio every day has the effect of ignoring corporate actions.

Run the tool to create the index:

```fish
poetry run poetry run create --index-type multiple_equity_basket --config-file-path /path/to/template.json --prod-run
poetry run poetry run create --index-type multiple_equity_basket --config-file-path /path/to/template_no_corax.json --prod-run
```

## Accessing the returns

The above will launch an index titled `{name}` into the namespace (`test` in this example).

After a few moments, (depending on how far back the `base_date` is), you will recieve the full historical Corporate Actions email for historical corporate actions since the `base_date`.

To access returns, you have four options:
1. You can use the daily emails (and the email that was sent upon creation with the historical return)

![Alt text](../tr_decrement/imgs/tr_returns_email.png?raw=true "Title")

2. You can navigate to the website at `https://merqube.com/index/{name}`

![Alt text](../tr_decrement/imgs/tr_website.png?raw=true "Title")

3. You can use the API directly:

     curl -H "Authorization: APIKEY YOUR_API_KEY "https://api.merqube.com/security/index?name={name}&metrics=price_return&start_date=2023-06-01&end_date=2023-06-05" | jq .

(I set `start_date` and `end_date` in the above to limit the results; you can change these or remove these parameters for the full history)

```json
{
  "results": [
    {
      "eff_ts": "2023-06-01T00:00:00",
      "id": "6f16b84e-e760-4ba2-bd27-ccba9539ddee",
      "name": "tjc_multi_basket_index",
      "price_return": 1367.4853398823066
    },
    {
      "eff_ts": "2023-06-02T00:00:00",
      "id": "6f16b84e-e760-4ba2-bd27-ccba9539ddee",
      "name": "tjc_multi_basket_index",
      "price_return": 1373.9951714080958
    },
    {
      "eff_ts": "2023-06-05T00:00:00",
      "id": "6f16b84e-e760-4ba2-bd27-ccba9539ddee",
      "name": "tjc_multi_basket_index",
      "price_return": 1390.4528182450981
    }
  ]
}
```


4. You can use this client library to fetch returns, portfolios, etc:

```python
from merqube_client_lib.api_client.merqube_client import MerqubeAPIClientSingleIndex
from merqube_client_lib.util import get_token

client = MerqubeAPIClientSingleIndex(index_name="tjc_multi_basket_index", token=get_token())
df = client.get_metrics(metrics=["price_return"])
print(df)  # a pandas dataframe
ports = client.get_portfolio()
```

which produces a dataframe:

```python
                   eff_ts                                    id                    name  price_return
0     2000-01-04T00:00:00  6f16b84e-e760-4ba2-bd27-ccba9539ddee  tjc_multi_basket_index   1000.000000
1     2000-01-05T00:00:00  6f16b84e-e760-4ba2-bd27-ccba9539ddee  tjc_multi_basket_index   1000.000000
2     2000-01-06T00:00:00  6f16b84e-e760-4ba2-bd27-ccba9539ddee  tjc_multi_basket_index   1000.000000
3     2000-01-07T00:00:00  6f16b84e-e760-4ba2-bd27-ccba9539ddee  tjc_multi_basket_index   1000.000000
4     2000-01-10T00:00:00  6f16b84e-e760-4ba2-bd27-ccba9539ddee  tjc_multi_basket_index   1000.000000
...                   ...                                   ...                     ...           ...
5895  2023-06-09T00:00:00  6f16b84e-e760-4ba2-bd27-ccba9539ddee  tjc_multi_basket_index   1339.439473
5896  2023-06-12T00:00:00  6f16b84e-e760-4ba2-bd27-ccba9539ddee  tjc_multi_basket_index   1346.347949
5897  2023-06-13T00:00:00  6f16b84e-e760-4ba2-bd27-ccba9539ddee  tjc_multi_basket_index   1348.044646
5898  2023-06-14T00:00:00  6f16b84e-e760-4ba2-bd27-ccba9539ddee  tjc_multi_basket_index   1348.391181
5899  2023-06-15T00:00:00  6f16b84e-e760-4ba2-bd27-ccba9539ddee  tjc_multi_basket_index   1367.694641
```

# Updating and fetching the portfolio (rebalancing)

In this demo, our initial portfolio contained a base date all in cash, and a single portfolio effective 2022-03-11. If we fetch all of the portfolios, we will see these two dated open portfolios:

```python
from merqube_client_lib.api_client.merqube_client import MerqubeAPIClientSingleIndex
from merqube_client_lib.util import get_token

client = MerqubeAPIClientSingleIndex(index_name="tjc_multi_basket_index", token=get_token())

print(client.get_target_portfolio())
```

will show:

```json
[
    {
        "eff_ts": "2000-01-04T00:00:00",
        "target_portfolio": {
            "positions": [
                {"amount": 1000.0, "asset_type": "CASH", "identifier": "USD", "identifier_type": "CURRENCY_CODE"}
            ],
            "timestamp": "2000-01-04T00:00:00",
            "unit_of_measure": "SHARES",
        },
    },
    {
        "eff_ts": "2022-03-11T00:00:00",
        "target_portfolio": {
            "positions": [
                {"amount": -0.2512355, "asset_type": "EQUITY", "identifier": "AAPL.OQ", "identifier_type": "RIC"},
                {
                    "amount": -0.28782633781297995,
                    "asset_type": "EQUITY",
                    "identifier": "AMZN.OQ",
                    "identifier_type": "RIC",
                },
                {"amount": 0.78687756527879, "asset_type": "EQUITY", "identifier": "GOOG.OQ", "identifier_type": "RIC"},
                {"amount": 0.8687756527878999, "asset_type": "EQUITY", "identifier": "A.N", "identifier_type": "RIC"},
                {"amount": 60.0, "asset_type": "CASH", "identifier": "USD", "identifier_type": "CURRENCY_CODE"},
            ],
            "timestamp": "2022-03-11T00:00:00",
            "unit_of_measure": "SHARES",
        },
    },
]
```

Next, we are going to perform a rebalance:

```fish
poetry run update_portfolio --index-name tjc_multi_basket_index --constituents-csv-path ./portfolios_update.csv --prod-run
```

Now, if we run the same code above again, we will see those two dated portfolios, plus a new one:

```json
...,
{
    "eff_ts": "2023-12-14T00:00:00",
    "target_portfolio": {
        "positions": [
            {"amount": 0.5, "asset_type": "EQUITY", "identifier": "AMZN.OQ", "identifier_type": "RIC"},
            {"amount": 0.5, "asset_type": "EQUITY", "identifier": "GOOG.OQ", "identifier_type": "RIC"},
            {"amount": 60.0, "asset_type": "CASH", "identifier": "USD", "identifier_type": "CURRENCY_CODE"},
        ],
        "timestamp": "2023-12-14T00:00:00",
        "unit_of_measure": "SHARES",
    },
}
```

We can also use the start_date and end_date parameters to limit the results to a time range. For example,
we can fetch a given days rebalance (assuming it has one) by setting them the same:

```python
print(client.get_target_portfolio(start_date=pd.Timestamp("2023-12-14"), end_date=pd.Timestamp("2023-12-14")))
```

which will just print the last portfolio entry.

Finally, let's rebalance once more:

```fish
poetry run update_portfolio --index-name tjc_multi_basket_index --constituents-csv-path ./portfolios_update_2.csv --prod-run
```

Fetching the portfolios now will include all four:

```python
print(client.get_target_portfolio())
```

shows:

```json
[
    {
        "eff_ts": "2000-01-04T00:00:00",
        "target_portfolio": {
            ...
        },
    },
    {
        "eff_ts": "2022-03-11T00:00:00",
        "target_portfolio": {
            ...
        },
    },
    {
        "eff_ts": "2023-12-14T00:00:00",
        "target_portfolio": {
            ...
        },
    },
    {
        "eff_ts": "2024-03-15T00:00:00",
        "target_portfolio": {
            "positions": [
                {"amount": 1.0, "asset_type": "EQUITY", "identifier": "AMZN.OQ", "identifier_type": "RIC"},
                {"amount": 90.0, "asset_type": "CASH", "identifier": "USD", "identifier_type": "CURRENCY_CODE"},
            ],
            "timestamp": "2024-03-15T00:00:00",
            "unit_of_measure": "SHARES",
        },
    },
]
```

# Comparing dividend reinvestment to without

Let's launch two indices, with the same basket, one with dividend reinvestment and one without.
Fill in the two templates provided (`example_mult.json`, `example_mult_no_corax.json`) and create them using the above:

```bash
poetry run poetry run create --index-type=multiple_equity_basket --config-file-path /path/to/mult_no_corax.json --prod-run
poetry run poetry run create --index-type=multiple_equity_basket --config-file-path /path/to/mult_no_corax.json --prod-run
```

There is an example portfolio in this dir, `./portfolios_initial_corax_compare.csv` that has two constituents - 100 shares of Apple and Google both starting in 2015.
Having launched those two indices, one with dividend reinvestment, one without, we can see how the returns compare:

```python
from merqube_client_lib.api_client.merqube_client import MerqubeAPIClient
from merqube_client_lib.util import get_token

client = MerqubeAPIClient(token=get_token())
df = client.get_security_metrics(
    sec_type="index",
    sec_names=["tjc_multi_basket_index_wout_divs", "tjc_multi_basket_index_w_divs"],
    metrics=["price_return"],
)
df = df.pivot(index="eff_ts", columns="name", values="price_return").query(
    "eff_ts > '2015-01-08'"
)

print(df)
```

shows:

```python
name                 tjc_multi_basket_index_w_div6  tjc_multi_basket_index_wout_div6
eff_ts
2015-01-08T00:00:00                    1000.000000                        1000.00000
2015-01-09T00:00:00                    1000.000000                        1000.00000
2015-01-12T00:00:00                   60180.000000                       60180.00000
2015-01-13T00:00:00                   60640.000000                       60640.00000
2015-01-14T00:00:00                   61067.000000                       61067.00000
...                                            ...                               ...
2023-06-12T00:00:00                  328395.913152                      322898.80585
2023-06-13T00:00:00                  328363.815135                      322867.24513
2023-06-14T00:00:00                  328522.191693                      323022.97058
2023-06-15T00:00:00                  332236.102146                      326674.71289
2023-06-16T00:00:00                  328264.114550                      322769.21346
```

We can see that the div reinvestment generates about 5.5k in the index from 1/2015 to 6/2023.
