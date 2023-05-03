"""
pytest conftest
"""

from merqube_client_lib.mocker import mock_secapi_builder
from merqube_client_lib.secapi import client

mock_secapi = mock_secapi_builder(
    get_session_function_path="merqube_client_lib.session.get_merqube_session",
    get_client_function_path="merqube_client_lib.secapi.client.get_client",
    secapi_client_cache=client.secapi_client_cache,
)
