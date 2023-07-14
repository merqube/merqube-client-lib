#!/bin/sh

# Generates pydantic types from the OpenAPI schema
pip install datamodel-code-generator[http] --upgrade
curl https://api.merqube.com/api-raw > /tmp/openapi.yaml
datamodel-codegen --strict-types str bool --set-default-enum-member --enum-field-as-literal one --input-file-type openapi --input /tmp/openapi.yaml --output merqube_client_lib/pydantic_types.py --use-default --field-extra-keys-without-x-prefix x-default_factory --strict-nullable
black merqube_client_lib/pydantic_types.py
