# Creating Indices

This client library comes with a library of index templates.
The number of templates will grow.
Currently, there are two templates:

1. Single equity total return indices - creates a single stock total return index on any RIC (Reuters). More input sources will be supported in the future.
1. Multiple equity (pre-corax adjusted) basket - creates an equity basket where the client provides rebalance portfolios

## Permissions
As discussed in (Overview), customer indices are in `namespaces`.
Your API key has access to create indices in one or more namespaces.

The official process and website page for creating, viewing, and deleting API Keys is coming - and it will allow you to view the permissions associated with each key.
A customer may have multiple namespaces for a variety of reasons (different internal teams, logical partitioning, etc).
Every manifest must specify the `namespace` that the index is to be created in.

## Bloomberg Tickers
Unfortunately, MerQube does not have API access to Bloomberg. Creating tickers to push your index levels to is currently a manual process.
You can email MerQube (`support at merqube dot com`) a list of tickers to create, and our support staff can create them for you.
After confirmation, you can reference those tickers in your index templates (see below) and your indices will push to those tickers.

We are working on improvements to make this as seamless as possible.

## Single Stock Total Return

The template for creating a single stock total return index (often abbreviated as a "TR") is found at:

    merqube_client_lib/templates/equity_baskets/single_stock_total_return_corax/template.json

This will create an index that produces the total return of the `underlying_ric`. It will backfill returns since `base_date`.

This index reinvests dividends and accounts for all corporate actions (stock splits, etc).

A client for creating Decrement Indices (or "Overlay") is coming, and those decrements are specified on these TR indices.

The process to create the index is:

1. `poetry install` of this library
2. copy the `template.json` and edit it per your index
3. `poetry run single_stock_tr --config-file-path /path/to/that/template`

## Multiple Stock Basket (No Corporate Actions)

The template for creating an equity basket where the client provides their own corporate action adjusted portfolio (daily, or at any interval) is found at:

    merqube_client_lib/templates/equity_baskets/multiple_no_corax/template.json

The process to create an index is the same as the above, except with `run multiple_no_corax`.


## Multiple Stock Basket (With Corporate Actions)

Coming Soon
