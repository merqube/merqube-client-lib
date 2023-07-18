"""
Module for mocking secapi, mostly for unit testing, but also for other components testing against secapi
"""
import importlib
import logging
from typing import Any, Callable, Optional
from unittest.mock import MagicMock

from cachetools import Cache

from merqube_client_lib.logging import get_module_logger

logger = get_module_logger(__name__, level=logging.DEBUG)


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

    def mock_secapi(
        monkeypatch,
        method_name_function_map: dict[str, Callable[..., Any]],
        session_func_map: dict[str, Callable[..., Any]] | None = None,
        **get_client_kwargs: Any,
    ) -> None:
        """
        get a client with some methods patched with swapout functions
        """
        if secapi_client_cache is not None:
            logger.debug("Clearing client cache")
            secapi_client_cache.clear()
        else:
            logger.debug("No client cache to clear")

        sess = MagicMock()

        if session_func_map is not None:
            for method_name, func in session_func_map.items():
                if getattr(sess, method_name) is None:
                    raise ValueError(f"Trying to patch a nonexisting session method: {method_name}")
                logger.debug(f"Mocking session method {method_name}")
                setattr(sess, method_name, func)

        def get_session(*args: Any, **kwargs: Any):
            logger.debug("Returning mocked session")
            return sess

        logger.debug(f"Mocking get_session call at {get_session_function_path}")
        monkeypatch.setattr(get_session_function_path, get_session)

        client = client_module.get_client(**get_client_kwargs)

        if "get_supported_secapi_types" not in method_name_function_map:
            logger.debug("Mocking get_supported_secapi_types")
            setattr(client, "get_supported_secapi_types", _sec_types)

        for method_name, func in method_name_function_map.items():
            if getattr(client, method_name) is None:
                raise ValueError(f"Trying to patch a nonexisting client method: {method_name}")
            logger.debug(f"Mocking method {method_name}")
            setattr(client, method_name, func)

        def get_client(*args: Any, **kwargs: Any):
            logger.debug("Returning mocked client")
            return client

        # now a get_client call from the main code will return this mocked client:
        logger.debug(f"Mocking get_client call at {get_client_function_path}")
        monkeypatch.setattr(get_client_function_path, get_client)

    return mock_secapi
