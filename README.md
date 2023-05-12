# merqube-client-lib
MerQube API Client Library (Python)
[![CircleCI](https://dl.circleci.com/status-badge/img/gh/merqube/merqube-client-lib/tree/main.svg?style=svg)](https://dl.circleci.com/status-badge/redirect/gh/merqube/merqube-client-lib/tree/main)


## Overview

This is a python client library for MerQube's public API.

### Project Status
This is a WIP release of an internal client library. This README will be updated when it is ready. More functionality will be added here over the coming weeks.

### Full Specification
A link-resolved OpenAPI spec is served from [here](https://api.merqube.com/api), and the raw YAML (unresolved, i.e., it contains remote references to other YAML) is served from [here](https://api.merqube.com/api-raw).
There is a browsable rendering of the OpenAPI (formerly Swagger) spec [here](https://www.merqube.com/api).

### Installation and requirements

This library can be installed from PyPi:

    pip install merqube-client-lib

It is currently `python3.10+`.

## API Concepts

### Main endpoints:
MerQube's public API has the following main components:
1. IndexAPI (`/index`): endpoints for managing index objects themselves (creation, deletion, and editing of indices), and also collecting some types of index information (e.g., portfolios).
2. SecAPI (`/security`): endpoints for collecting *security metrics* from indices and other security types. For example, daily returns and available intermediate calculations.
3. Apikey (`/apikey`): an API for managing API keys, which are used by this client (or as a `curl` header etc.) to authenticate as a user

### Permissions

While endpoints on `api.merqube` are publicly available, many of the resources are permissioned and require authorization to view (as discussed further below).
All objects in MerQube's universe are in a namespace, and MerQube's API is permissioned by namespace.

Objects in the `default` namespace are public and world-readable; for example, all indices served on `api.merqube.com/index` that can be seen without authentication.
Typically, these are MerQube branded indices.

Customer indices are typically in customer namespaces, and clients from those organizations have permissions to view those namespaces.
For example, clients from `MyBank` may be permissioned to the `mybank` namespace - when they query `api.merqube.com/index`, they will see the combination of all `default` (open) indices and all indices in `mybank`. There may be multiple namespaces per client.

### Names vs. IDs
There are several standard properties on every object in the MerQube API, most notably:
1. `name`: a name chosen by the user (on creation) that is unique across that resource type, e.g., no two indices have the same name
1. `namespace`: the permissioning namespace described above
1. `id`: an unchanging identifier for that index. While index names can be changed, identifiers cannot. They are permanent references to the object, which is why all API endpoints are UUID based (though you can search by name). The only way to "change" the id of an object is to delete it, and make another with the same name.
1. `status`: a metadata block containing information about creation and edit times. This block also serves as a token when making edits. It must be supplied on `PUT` or `PATCH`, and the write is only accepted if the status block matches the current object in storage (i.e., it verifies you are updating the current object and not an outdated copy).

### Index vs. Index-securities

Creating an Index in MerQube's API with name `X` in namespace `Y`, automatically creates two securities in the SecAPI:
1. An `index` security that holds all returns and metrics for that index
2. An `intraday_index` security for the same, except that it will only have metrics if the index is a real time index.

These securities, located on the SecAPI (`/security/index` and `/security/intraday_index` respectively), will have different IDs than the index, but have the same name `X` and namespace `Y` as the index.
They all move in unison; if the index name or namespace is changed, the name and namespace of its linked securities also change to match.


### Types

MerQube makes heavy use of [pydantic](https://docs.pydantic.dev/latest/)

The script `./generate_types.sh` at the root of this repo will:
1. Pull down the latest production API (OpenAPI spec)
1. generate a file `merqube_client_lib/pydantic_types.py

We may eventually push this as a package to PyPi as well.

Note, we use a [third party tool](https://github.com/koxudaxi/datamodel-code-generator) to generate this, and other than the CLI options, do not have control over the layout or ordering of this file.

These types can then be used as classes in any code forming indices (finally, using pydantic's `.json` or `.dict` method to convert before sending to the API).
The most relevent types to clients are probably:
1. `IndexDefinitionPost`: the schema for new index creation (`POST`)
1. `IndexDefinitionPatchPutGet`: the schema for the return from `GET`s, and what would be supplied on `PUT` and `PATCH`. This model contains server side generated fields like `Status` that are illegal on `POST`.
1. `SecurityMetrics`: the schema for every record in the SecAPI. This is what can be expected on all reads.
