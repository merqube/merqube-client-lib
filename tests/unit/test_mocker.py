"""
Test the Secapi mocker
"""
from unittest.mock import MagicMock

import pytest

from merqube_client_lib.api_client.merqube_client import client_cache, get_client
from merqube_client_lib.mocker import _sec_types, mock_secapi_builder
from tests.conftest import mock_secapi
from tests.unit.fixtures.dummy_secapi import get_client as dummy_client


def test_mocker(monkeypatch):
    """test mocking the client"""
    mock_mt = MagicMock(return_value={"foo": "1234", "bar": "5678"})
    mock_secapi(monkeypatch, method_name_function_map={"get_security_definitions_mapping_table": mock_mt})

    client = get_client()
    assert client.get_security_definitions_mapping_table(sec_type="index") == {"foo": "1234", "bar": "5678"}


def test_mock_secapi_builder_fail():
    """test mocking with invalid paths"""
    with pytest.raises(ModuleNotFoundError):
        mock_secapi_builder(
            get_session_function_path="nonexistent.session.function",
            get_client_function_path="nonexistent.client.function",
        )


@pytest.mark.parametrize("with_cache", [False, True], ids=["without-cache", "with-cache"])
@pytest.mark.parametrize("with_custom_sec_types", [False, True], ids=["default-sec-types", "custom-sec-types"])
def test_mock_secapi_builder(monkeypatch, with_cache, with_custom_sec_types):
    """test successful mocking using a dummy client"""
    cache = MagicMock(wraps=client_cache)

    dummy_mocker = mock_secapi_builder(
        get_session_function_path="tests.unit.fixtures.dummy_secapi._get_session",
        get_client_function_path="tests.unit.fixtures.dummy_secapi.get_client",
        secapi_client_cache=cache if with_cache else None,
    )

    extra_method_map = (
        {"get_supported_secapi_types": MagicMock(return_value=["custom"])} if with_custom_sec_types else {}
    )

    dummy_mocker(
        monkeypatch=monkeypatch,
        method_name_function_map={
            "get_futures_contracts_from_secapi": MagicMock(return_value=["mocked"]),
            **extra_method_map,
        },
    )

    assert cache.clear.called == with_cache
    client = dummy_client()
    if with_custom_sec_types:
        assert client.get_supported_secapi_types() != _sec_types()
        assert client.get_supported_secapi_types() == ["custom"]
    else:
        assert client.get_supported_secapi_types() == _sec_types()
