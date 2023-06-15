# Creating Indices

This client library comes with a library of index templates.
The number of templates will grow.
Currently, there are three templates:

1. Single equity total return indices - creates a single stock total return index on any RIC (Reuters). More input sources will be supported in the future.
1. Multiple equity (pre-corax adjusted, or MerQube handled corporate actions) basket
1. Decrement - a decrement index on top of a single total return index

## Permissions
As discussed in (Overview), customer indices are in `namespaces`.
Your API key has access to create indices in one or more namespaces.

To create any indices with this library, you must set the env `MERQ_API_KEY`.

The official process and website page for creating, viewing, and deleting API Keys is coming - and it will allow you to view the permissions associated with each key.
A customer may have multiple namespaces for a variety of reasons (different internal teams, logical partitioning, etc).
Every manifest must specify the `namespace` that the index is to be created in.

## Bloomberg Tickers
Unfortunately, Bloomberg does not provide MerQube API access to create tickers. Creating tickers to push your index levels to is currently a manual process.
You can email MerQube (`support at merqube dot com`) a list of tickers to create, and our support staff can create them for you.
After confirmation, you can reference those tickers in your index templates (see below) and your indices will push to those tickers.

We are working on improvements to make this as seamless as possible.

## Template Locations

The template configuration for creating each of the index types above are found at:

    merqube_client_lib/templates/equity_baskets/single_stock_total_return_corax/template.json
    merqube_client_lib/templates/equity_baskets/decrement/template.json
    merqube_client_lib/templates/equity_baskets/multiple_equity_basket/template.json

The process to create an index is:

1. `poetry install` of this library
1. copy the `template.json` and edit it per your index
1. `export MERQ_API_KEY..`  (can also set this in your environment config)
1. `poetry run create --index-type=TYPE --config-file-path=/path/to/template/you/copied/and/edited`

Add `--prod-run` to create the index in production, rather than just templating/logging it.
