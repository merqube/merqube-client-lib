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


def _json_helper(path):
    return json.load(open(os.path.join(here, "fixtures", path + ".json")))


@pytest.fixture(autouse=True)
def reset_global():
    merqube_client.client_cache.clear()


@pytest.fixture
def v1_multi():
    return _json_helper("v1_multi")


@pytest.fixture
def v1_ss():
    return _json_helper("v1_ss")


@pytest.fixture
def v1_decrement():
    return _json_helper("v1_decrement")


@pytest.fixture
def templated_ss():
    return _json_helper("templated_ss")


@pytest.fixture
def templated_mult():
    return _json_helper("templated_mult")


@pytest.fixture
def templated_mult_ports():
    return _json_helper("templated_mult_ports")
