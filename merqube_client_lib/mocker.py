"""
Module for mocking secapi, mostly for unit testing, but also for other components testing against secapi
"""

import importlib
from typing import Any, Callable, Optional
from unittest.mock import MagicMock

from cachetools import Cache


def _sec_types() -> list[dict[str, str]]:
    """fixed map for mocking valid sectypes"""
    return [
        {"name": "crypto_asset"},
        {"name": "custom"},
        {"name": "equity"},
        {"name": "exchange"},
        {"name": "futures_contract"},
        {"name": "futures_option"},
        {"name": "futures_root"},
        {"name": "fx"},
        {"name": "index"},
        {"name": "intraday_index"},
        {"name": "interest_rate"},
        {"name": "economic_data"},
    ]


def mock_secapi_builder(
    get_session_function_path: str, get_client_function_path: str, secapi_client_cache: Optional[Cache] = None  # type: ignore
) -> Callable[..., None]:
    """
    Builds the `mock_secapi` function used for the API for its tests.

    ```
    mock_secapi = mock_secapi_builder(
        get_session_function_path="dataapi.runners.sec_client._get_dataapi_session",
        get_client_function_path="dataapi.runners.sec_client.get_client",
        secapi_client_cache=sec_client.client_cache
    )
    ```

    Then in your tests, you can use `mock_secapi`

    ```
    mock_secapi(
        monkeypatch=monkeypatch,
        method_name_function_map={
            "get_security_definitions_mapping_table": MagicMock(return_value={}),
            "_post_dedupe": MagicMock(),
            ...
        },
    )
    ```
    """
    for function in [get_session_function_path, get_client_function_path]:
        # Checks if all the function exists
        importlib.find_loader(function)

    client_function_module_name = get_client_function_path[: get_client_function_path.rindex(".")]
    client_module = importlib.import_module(client_function_module_name)

    def mock_secapi(monkeypatch, method_name_function_map: dict[str, Callable[..., Any]]) -> None:
        """
        get a client with some methods patched with swapout functions
        """
        if secapi_client_cache is not None:
            secapi_client_cache.clear()

        sess = MagicMock()
        monkeypatch.setattr(get_session_function_path, MagicMock(return_value=sess))

        client = client_module.get_client()

        if "get_supported_secapi_types" not in method_name_function_map:
            setattr(client, "get_supported_secapi_types", _sec_types)

        # inside

        for method_name, func in method_name_function_map.items():
            if getattr(client, method_name) is None:
                raise ValueError("Trying to patch a function that doesnt exist in the client")
            setattr(client, method_name, func)

        def get_client(*args: Any, **kwargs: Any):
            return client

        # now a get_client call from the main code will return this mocked client:
        monkeypatch.setattr(get_client_function_path, get_client)

    return mock_secapi
