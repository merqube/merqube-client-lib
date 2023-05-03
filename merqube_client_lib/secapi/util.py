"""
Internal helper utility. Not intended for client use.
"""
from functools import wraps
from typing import Any, Callable, Iterable, Optional, Union

from cachetools import TTLCache, cached

from merqube_client_lib.constants import DEFAULT_TTL_CACHE
from merqube_client_lib.session import MerqubeAPISession
from merqube_client_lib.types.secapi import SecAPIRecordsResponse


def sec_validator_single(func: Callable[..., Any]) -> Callable[..., Any]:
    """decorator for validating functions that should pass a valid sec_type and a single sec_id or sec_name"""

    @wraps(func)
    def wrapper(
        *,
        sec_type: str,
        session: MerqubeAPISession,
        sec_id: str | None = None,
        sec_name: str | None = None,
        **kwargs: Any,
    ) -> Any:
        supported_types = get_supported_secapi_types(session=session)
        assert sec_type in supported_types, f"sec_type must be one of {supported_types}"
        assert sec_id or sec_name, "Must provide either sec_id or sec_name"
        assert not (sec_id and sec_name), "Must provide either sec_id or sec_name, not both"
        return func(sec_type=sec_type, session=session, sec_id=sec_id, sec_name=sec_name, **kwargs)

    return wrapper


def sec_validator_multiple(func: Callable[..., Any]) -> Callable[..., Any]:
    """decorator for validating functions that should pass a valid sec_type and one or more sec_ids or sec_names"""

    @wraps(func)
    def wrapper(
        *,
        sec_type: str,
        session: MerqubeAPISession,
        sec_names: Optional[str | Iterable[str]] = None,
        sec_ids: Optional[str | Iterable[str]] = None,
        **kwargs: Any,
    ) -> Any:
        supported_types = get_supported_secapi_types(session=session)
        assert sec_type in supported_types, f"sec_type must be one of {supported_types}"
        assert sec_ids or sec_names, "Must provide either sec_ids or sec_names"
        assert not (sec_ids and sec_names), "Must provide either sec_ids or sec_names, not both"
        return func(sec_type=sec_type, session=session, sec_ids=sec_ids, sec_names=sec_names, **kwargs)

    return wrapper


def collection_helper(
    url: str,
    session: MerqubeAPISession,
    query_options: dict[str, Union[str | None, Iterable[str] | None]],
) -> SecAPIRecordsResponse:
    """
    common function to /security metrics and definitions
    """
    options: dict[str, str | list[str]] = {}

    for qo, v in query_options.items():
        if v is not None:
            options[qo] = v if isinstance(v, str) else ",".join(v)

    return session.get_collection(url, options=options)


@cached(cache=TTLCache(2, ttl=DEFAULT_TTL_CACHE))
def get_supported_secapi_types(session: MerqubeAPISession) -> list[str]:
    """
    Gets the list of currently supported security types
    """
    res = session.get_collection("/security")
    return [x["name"] for x in res]
