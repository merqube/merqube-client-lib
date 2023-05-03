"""
Main SecAPI client class
"""
import operator
from typing import Any, Iterable, Optional

from cachetools import LRUCache, TTLCache, cached, cachedmethod

from merqube_client_lib.constants import DEFAULT_TTL_CACHE
from merqube_client_lib.session import MerqubeAPISession, get_merqube_session
from merqube_client_lib.types.secapi import (
    AddlSecapiOptions,
    MappingTable,
    SecapiMetricDefinition,
    SecAPIRecordsResponse,
)


class _ClientBase:
    """
    base class that contains validation functions
    """

    def __init__(
        self,
        session: Optional[MerqubeAPISession] = None,
        token: Optional[str] = None,
        **session_kwargs: Any,
    ):
        self.session = session or get_merqube_session(token=token, **session_kwargs)
        self.type_cache = TTLCache(1, ttl=DEFAULT_TTL_CACHE)  # type: ignore

    def _collection_helper(
        self,
        *,
        url: str,
        query_options: dict[str, str | Iterable[str] | None] | None = None,
    ) -> SecAPIRecordsResponse:
        """
        common function to /security metrics and definitions
        """
        options: dict[str, str | list[str]] = {}

        for qo, v in (query_options or {}).items():
            if v is not None:
                options[qo] = v if isinstance(v, str) else ",".join(v)

        return self.session.get_collection(url=url, options=options)

    @cachedmethod(operator.attrgetter("type_cache"))
    def _validate_secapi_type(self, sec_type: str) -> None:
        """Validate security_type"""
        res = self.session.get_collection("/security")
        assert sec_type in (supported_types := [x["name"] for x in res]), f"sec_type must be one of {supported_types}"

    def _validate_single(self, *, sec_type: str, sec_id: str | None = None, sec_name: str | None = None) -> None:
        """Validate the input for functions that query for a single security"""
        self._validate_secapi_type(sec_type=sec_type)
        assert sec_id or sec_name, "Must provide either sec_id or sec_name"
        assert not (sec_id and sec_name), "Must provide either sec_id or sec_name, not both"

    def _validate_multiple(
        self,
        *,
        sec_type: str,
        sec_names: Optional[str | Iterable[str]] = None,
        sec_ids: Optional[str | Iterable[str]] = None,
    ) -> None:
        """Validate the input for functions that query for one or more securities"""
        self._validate_secapi_type(sec_type=sec_type)
        assert sec_ids or sec_names, "Must provide either sec_ids or sec_names"
        assert not (sec_ids and sec_names), "Must provide either sec_ids or sec_names, not both"


class SecAPIClient(_ClientBase):
    """
    Secapi client class
    """

    def __init__(
        self,
        session: Optional[MerqubeAPISession] = None,
        token: Optional[str] = None,
        **session_kwargs: Any,
    ):
        """
        We use partials to preserve types, see my SO post here
        https://stackoverflow.com/questions/73145008/python-is-there-a-version-of-functools-wraps-that-preserves-mypy-strict
        """
        super().__init__(session=session, token=token, **session_kwargs)

    def get_metrics_for_security(
        self,
        *,
        sec_type: str,
        sec_id: str | None = None,
        sec_name: str | None = None,
    ) -> list[SecapiMetricDefinition]:
        """
        Get the list of metrics that are currently available for a security
        Can query by id or name
        """
        self._validate_single(sec_type=sec_type, sec_id=sec_id, sec_name=sec_name)
        return self.session.get_collection(
            f"/security/{sec_type}/{sec_id}/metrics" if sec_id else f"/security/{sec_type}/metrics?name={sec_name}"
        )

    def get_security_definitions_mapping_table(
        self,
        *,
        sec_type: str,
        sec_names: Optional[str | Iterable[str]] = None,
        sec_ids: Optional[str | Iterable[str]] = None,
        addl_options: Optional[AddlSecapiOptions] = None,
    ) -> MappingTable:
        """
        Lists defined (and permissioned) securities for a type.
        Optionally filters by a list of securities.
        Returns a mapping table; either name -> id, or id -> name
        """
        # this function can be called with no ids/names to get a list of all permissioned securities
        self._validate_secapi_type(sec_type=sec_type)
        query_options: dict[str, str | Iterable[str] | None] = {"names": sec_names, "ids": sec_ids}
        if addl_options is not None:
            query_options.update(addl_options)

        rec_data = self._collection_helper(
            url=f"/security/{sec_type}",
            query_options=query_options,
        )

        return {c["id"]: c["name"] for c in rec_data} if sec_ids else {c["name"]: c["id"] for c in rec_data}


secapi_client_cache: LRUCache = LRUCache(maxsize=256)  # type: ignore


@cached(cache=secapi_client_cache)
def get_client(token: Optional[str] = None, **session_kwargs: Any) -> SecAPIClient:
    """
    Cached; returns a secapi client for token
    """
    return SecAPIClient(token=token, **session_kwargs)
