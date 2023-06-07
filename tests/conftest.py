"""
pytest conftest
"""
import json
import os

import pytest

from merqube_client_lib.api_client import merqube_client
from merqube_client_lib.mocker import mock_secapi_builder

here = os.path.dirname(os.path.abspath(__file__))
mock_secapi = mock_secapi_builder(
    get_session_function_path="merqube_client_lib.session.get_merqube_session",
    get_client_function_path="merqube_client_lib.api_client.merqube_client.get_client",
    secapi_client_cache=merqube_client.client_cache,
)


@pytest.fixture(autouse=True)
def reset_global():
    merqube_client.client_cache.clear()


@pytest.fixture
def v1_multi():
    return json.load(open(os.path.join(here, "unit/fixtures/v1_multi.json")))


@pytest.fixture
def v1_ss():
    return json.load(open(os.path.join(here, "unit/fixtures/v1_ss.json")))


@pytest.fixture
def v1_decrement():
    return json.load(open(os.path.join(here, "unit/fixtures/v1_decrement.json")))
