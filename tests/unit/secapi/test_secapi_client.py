"""
Tests for the secapi client
"""
from unittest.mock import MagicMock

from merqube_client_lib.secapi.client import get_client
from tests.conftest import mock_secapi


def test_public_client():
    """test instantiating without credentials"""
    # twice to trigger cache
    public = get_client()
    public2 = get_client()
    assert public is public2


def test_mocker(monkeypatch):
    """test mocking the client"""
    mock_mt = MagicMock(return_value={"foo": "1234", "bar": "5678"})
    mock_secapi(monkeypatch, method_name_function_map={"get_security_definitions_mapping_table": mock_mt})

    client = get_client()
    assert client.get_security_definitions_mapping_table(sec_type="index") == {"foo": "1234", "bar": "5678"}
