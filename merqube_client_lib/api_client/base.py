"""
Base class for all Merqube API Clients
"""
import logging
import operator
from collections import abc
from copy import deepcopy
from functools import wraps
from typing import Any, Callable, Iterable, Optional, cast

import pandas as pd
from cachetools import TTLCache, cachedmethod

# import like this so monkeypatch works as expected:
from merqube_client_lib import session
from merqube_client_lib.constants import DEFAULT_CACHE_TTL
from merqube_client_lib.logging import get_module_logger
from merqube_client_lib.pydantic_types import IndexDefinitionPatchPutGet as Index
from merqube_client_lib.pydantic_types import IndexDefinitionPost, RunState
from merqube_client_lib.session import MerqubeAPISession
from merqube_client_lib.types import Manifest, ManifestList, ResponseJson
from merqube_client_lib.types.secapi import (
    AddlSecapiOptions,
    MappingTable,
    SecapiMetricDefinition,
    SecAPIRecordsResponse,
)
from merqube_client_lib.util import (
    batch_post_payload,
    freezable_utcnow_ts,
    pydantic_to_dict,
)

EMPTY_RES: ResponseJson = {}
logger = get_module_logger(__name__, level=logging.DEBUG)


def _name_or_id(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    decorator to allow passing either id or name to a function
    """

    @wraps(func)
    def wrapped(
        self: Any, *args: Any, index_id: str | None = None, index_name: str | None = None, **kwargs: Any
    ) -> Any:
        assert (
            index_name or index_id and (not (index_name and index_id))
        ), "Must specify exactky one of index_name/index_id via kwarg"
        return func(self, *args, index_id=index_id, index_name=index_name, **kwargs)

    return wrapped


class _MerqubeApiClientBase:
    """
    base class that contains validation functions
    """

    def __init__(
        self,
        user_session: Optional[session.MerqubeAPISession] = None,
        token: Optional[str] = None,
        **session_kwargs: Any,
    ):
        self.session = user_session or session.get_merqube_session(token=token, **session_kwargs)

    def _collection_helper(
        self,
        *,
        url: str,
        query_options: dict[str, str | Iterable[str] | None] | None = None,
        raise_perm_errors: bool = False,
    ) -> ManifestList:
        """
        common function to /security metrics and definitions
        """
        options: dict[str, str | list[str]] = {}

        for qo, v in (query_options or {}).items():
            if v is not None:
                options[qo] = v if isinstance(v, str) else ",".join(v)

        return self.session.get_collection(url=url, options=options, raise_perm_errors=raise_perm_errors)


class _IndexAPIClient(_MerqubeApiClientBase):
    """
    Indexapi class that contains methods that deal with multiple indices, creation of indices etc
    """

    def get_index_defs(
        self, index_names: str | list[str] | None = None, include_nonprod: bool = False
    ) -> dict[str, Manifest]:
        """
        Get index definitions for specified names, or all permissioned indices as a dictionary with ids as keys and index definitions as values

        supports index_names:
        - XXX - single name
        - XXX,YYY - comma separated names
        - [XXX,YYY] - list of names

        Note that MerQube's "collection apis" never return a 404 - these are search apis, and will return an empty list if no results are found
        """

        endpoint = "/index"
        if include_nonprod:
            endpoint += "?type=all"

        if not index_names:
            all_indices = self.session.get_collection(endpoint)
            return {i["id"]: i for i in all_indices}

        names_arg = index_names if isinstance(index_names, str) else ",".join(index_names)

        prod_clause = "&type=all" if include_nonprod else ""
        url = f"/index?names={names_arg}{prod_clause}"
        res = self.session.get_collection(url)
        return {i["id"]: i for i in res}

    def get_indices_in_namespace(self, namespace: str) -> list[Index]:
        """
        Get all indices in a given namespace
        """
        return [
            Index.parse_obj(x)
            for x in self.session.get_collection(f"/index?namespace={namespace}", raise_perm_errors=True)
        ]

    def create_index(self, index_def: IndexDefinitionPost) -> ResponseJson:
        """
        Create an index
        Returns a dictionary containing the id of the index and its related securities (index, intraday_index)

        TODO: examples and index templates to be added to this repo.
        """
        return cast(ResponseJson, self.session.post("/index", json=pydantic_to_dict(index_def)).json())

    def replace_index(self, index_def: Index) -> ResponseJson:
        """
        Update (full object replacement) an index
        """
        return cast(dict[str, str], self.session.put(f"/index/{index_def.id}", json=pydantic_to_dict(index_def)).json())

    def replace_target_portfolio(self, index_id: str, target_portfolio: dict[str, Any]) -> ResponseJson:
        """
        Target portfolios are a PUT, not a POST, because an index can only have one active portfolio at a given time.
        "Last one wins", and it is not defined to have two+ active portfolios for the same timestamp.

        Internally (server side) all the history is kept, but only the latest one is used , and only the latest one is retrievable via this client.
        That is, if you PUT port1, then port2, (either via direct API or this library) port2 is always the one that is read on the next index run.
        Moreover, future portfolios can be posted at any time, but wont be considered by the index until that day.

        (You can get the index id by doing get_index_manifest(index_name)["id"])
        """
        return cast(ResponseJson, self.session.put(f"/index/{index_id}/target_portfolio", json=target_portfolio).json())

    @_name_or_id
    def get_index_manifest(self, index_name: str | None = None, index_id: str | None = None) -> Manifest:
        """
        Get the model for a given index
        """
        if index_name:
            return cast(Manifest, self.session.get_collection_single(f"/index?name={index_name}"))
        return cast(Manifest, self.session.get_json(f"/index/{index_id}"))

    @_name_or_id
    def get_index_model(self, index_name: str | None = None, index_id: str | None = None) -> Index:
        """
        Get the model for a given index
        """
        msft = self.get_index_manifest(index_name=index_name, index_id=index_id)
        return Index.parse_obj(msft)

    @_name_or_id
    def index_post_model_from_existing(
        self, index_name: str | None = None, index_id: str | None = None, reset_specific_fields: bool = True
    ) -> IndexDefinitionPost:
        """
        Gets a model that can be posted to /index to create a new index from an existing index

        For safety reasons, by default, the name and namespace are reset.
        """
        source_dict = deepcopy(self.get_index_manifest(index_name=index_name, index_id=index_id))
        source_dict.pop("id")
        source_dict.pop("status")

        model = IndexDefinitionPost.parse_obj(source_dict)

        if not reset_specific_fields:
            return model

        model.name = "test"
        model.namespace = "test"

        return model

    @_name_or_id
    def get_last_index_run_state(self, index_name: str | None = None, index_id: str | None = None) -> RunState:
        """
        Get the status of the last index run
        """
        if index_name:
            index_id = self.get_index_manifest(index_name)["id"]

        return RunState.parse_obj(self.session.get_json(f"/index/{index_id}/run_state"))

    @_name_or_id
    def delete_index(self, index_name: str | None = None, index_id: str | None = None) -> ResponseJson:
        """
        Delete an index
        """
        if index_name:
            index_id = self.get_index_manifest(index_name)["id"]

        return cast(ResponseJson, self.session.delete(f"/index/{index_id}").json())

    @_name_or_id
    def lock_index(self, index_name: str | None = None, index_id: str | None = None) -> ResponseJson:
        """
        Lock an index.

        Locks/unlocks must be done in isolated operations; ie you cannot lock a manifest while changing anything else,
        similarly you cannot change anything else while unlocking a manifest.

        Locking an index prevents all writes (PUT/PATCH/DELETE) on that index until it is explicitly unlocked.
        """
        model = self.get_index_model(index_name=index_name, index_id=index_id)

        if (status := model.status).locked_after:
            logger.info("Index is already locked")
            return EMPTY_RES

        # we add a few seconds to handle clock skew - the server does not allow locks set in the past
        status.locked_after = (freezable_utcnow_ts() + pd.Timedelta(seconds=3)).isoformat()
        payload = {"status": pydantic_to_dict(status)}
        return cast(ResponseJson, self.patch_index(index_id=model.id, updates=payload, auto_status=False))

    @_name_or_id
    def unlock_index(self, index_name: str | None = None, index_id: str | None = None) -> ResponseJson:
        """
        Unlock an index; see "lock_index"
        """
        model = self.get_index_model(index_name=index_name, index_id=index_id)

        if (status := model.status).locked_after is None:
            logger.info("Index is already unlocked")
            return EMPTY_RES

        status.locked_after = None
        # None is a default and we want to explicitly set it:
        payload = {"status": pydantic_to_dict(status, exclude_none=False, exclude_defaults=False)}
        return cast(ResponseJson, self.patch_index(index_id=model.id, updates=payload, auto_status=False))

    @_name_or_id
    def patch_index(
        self,
        *,
        index_name: str | None = None,
        index_id: str | None = None,
        updates: Manifest | None = None,
        auto_status: bool = True,
    ) -> ResponseJson:
        """
        Patch an index - updates is a partial index manifest
        (You can get the index id by doing get_index_manifest(index_name)["id"])

        auto_status:  status is required on all PUT/PATCH to prevent write conflicts, its a write token certifying that
        the object youre updating is the latest version. You probably always want this to be set
        """
        if not updates:
            return EMPTY_RES

        if auto_status:
            updates["status"] = self.get_index_manifest(index_name=index_name, index_id=index_id)["status"]

        return cast(ResponseJson, self.session.patch(f"/index/{index_id}", json=updates).json())


class _SecAPIClient(_MerqubeApiClientBase):
    """
    Secapi client class
    """

    def __init__(
        self,
        user_session: Optional[MerqubeAPISession] = None,
        token: Optional[str] = None,
        **session_kwargs: Any,
    ):
        super().__init__(user_session=user_session, token=token, **session_kwargs)

        self.type_cache = TTLCache(1, ttl=DEFAULT_CACHE_TTL)  # type: ignore

    def get_supported_secapi_types(self) -> list[dict[str, str]]:
        """
        Get the list of supported security types
        """
        return self.session.get_collection(url="/security")

    @cachedmethod(operator.attrgetter("type_cache"))
    def _validate_secapi_type(self, sec_type: str) -> None:
        """Validate security_type"""
        assert sec_type in (
            supported_types := [x["name"] for x in self.get_supported_secapi_types()]
        ), f"sec_type must be one of {supported_types}"

    def _validate_single(self, *, sec_type: str, sec_id: str | None = None, sec_name: str | None = None) -> None:
        """Validate the input for functions that query for a single security"""
        self._validate_secapi_type(sec_type=sec_type)
        assert sec_id or sec_name, "Must provide either sec_id or sec_name"
        assert not (sec_id and sec_name), "Must provide either sec_id or sec_name, not both"

    def _validate_multiple(
        self,
        *,
        sec_type: str,
        sec_names: str | Iterable[str] | None = None,
        sec_ids: str | Iterable[str] | None = None,
        metrics: str | Iterable[str] | None = None,
    ) -> None:
        """Validate the input for functions that query for one or more securities"""
        self._validate_secapi_type(sec_type=sec_type)

        assert not (sec_ids and sec_names), "Must provide either sec_ids or sec_names, not both"

        for param in [sec_ids, sec_names, metrics]:
            if param:
                assert isinstance(param, (str, abc.Iterable))

    def _validate_chunking_options(
        self,
        *,
        metrics: str | Iterable[str],
        sec_names: str | Iterable[str] | None = None,
        sec_ids: str | Iterable[str] | None = None,
        addl_options: AddlSecapiOptions | None = None,
        metrics_chunk_size: int | None = None,
        securities_chunk_size: int | None = None,
    ) -> None:
        """the user wants to chunk by either metrics or securities"""
        if addl_options and addl_options.get("raw") == "true":
            raise NotImplementedError("Chunking while raw=true is not currently implemented")

        if metrics_chunk_size is not None and securities_chunk_size is not None:
            raise NotImplementedError("Chunking by both metrics and securities is not currently implemented")

        if metrics_chunk_size is not None:
            if isinstance(metrics, str):
                # this is what we get for trying to be nice and allow anything (single str)
                raise ValueError("Cannot use chunk size when metrics is a single string")

            if metrics_chunk_size < 1:
                raise ValueError("metrics_chunk_size cannot be < 1")

        if securities_chunk_size is not None:
            if securities_chunk_size < 1:
                raise ValueError("securities_chunk_size cannot be < 1")
            if not sec_names and not sec_ids:
                raise ValueError(
                    "when specifying securities_chunk_size, either sec_names or sec_ids must be an iterable of string"
                )
            if isinstance(sec_names, str):
                raise ValueError("Cannot use chunk size when sec_names is a single string")

            if isinstance(sec_ids, str):
                raise ValueError("Cannot use chunk size when sec_ids is a single string")

    def _get_security_metrics_helper(
        self,
        *,
        sec_type: str,
        metrics: str | Iterable[str],
        sec_names: str | Iterable[str] | None = None,
        sec_ids: str | Iterable[str] | None = None,
        start_date: str | pd.Timestamp | None = None,
        end_date: str | pd.Timestamp | None = None,
        addl_options: AddlSecapiOptions | None = None,
        raise_perm_errors: bool = False,
    ) -> SecAPIRecordsResponse:
        """
        if sec_names and sec_ids are both []/None, it gets ALL securities.
        """

        metrics_list = [metrics] if isinstance(metrics, str) else list(metrics)

        # Join did not work correctly for KeyViews and Tuples are badly behaved, so we'll remap them to lists.
        sec_names_list = ([sec_names] if isinstance(sec_names, str) else list(sec_names)) if sec_names else []
        sec_ids_list = ([sec_ids] if isinstance(sec_ids, str) else list(sec_ids)) if sec_ids else []

        query_options = {
            "metrics": metrics_list,
            "names": sec_names_list,
            "ids": sec_ids_list,
            "start_date": pd.Timestamp(start_date).isoformat() if start_date else start_date,
            "end_date": pd.Timestamp(end_date).isoformat() if end_date else end_date,
        }
        if addl_options:
            query_options.update(addl_options)

        return self._collection_helper(
            url=f"/security/{sec_type}", query_options=query_options, raise_perm_errors=raise_perm_errors
        )

    def get_metrics_for_security(
        self,
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
        sec_type: str,
        sec_names: str | Iterable[str] | None = None,
        sec_ids: str | Iterable[str] | None = None,
        addl_options: AddlSecapiOptions | None = None,
        raise_perm_errors: bool = False,
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
            raise_perm_errors=raise_perm_errors,
        )

        return {c["id"]: c["name"] for c in rec_data} if sec_ids else {c["name"]: c["id"] for c in rec_data}

    def get_security_metrics(
        self,
        sec_type: str,
        metrics: str | Iterable[str],  # Secapi doesnt support fetching all metrics yet; cant be None
        sec_names: str | Iterable[str] | None = None,
        sec_ids: str | Iterable[str] | None = None,
        start_date: str | pd.Timestamp | None = None,
        end_date: str | pd.Timestamp | None = None,
        addl_options: AddlSecapiOptions | None = None,
        # if the secapi value is JSON, by default, pandas will flatten it into a dotted namespace
        # set this to control max_level: https://pandas.pydata.org/docs/reference/api/pandas.json_normalize.html
        # 0 means "dont normalize any JSONs
        normalize_level: int | None = None,
        metrics_chunk_size: int | None = None,
        securities_chunk_size: int | None = None,
        raise_perm_errors: bool = False,
    ) -> pd.DataFrame:
        """fetch security metrics from the SecAPI"""

        # Input validation
        self._validate_multiple(
            sec_type=sec_type,
            sec_names=sec_names,
            sec_ids=sec_ids,
            metrics=metrics,
        )
        assert metrics is not None, "Metrics cannot be None"

        params = {
            "sec_type": sec_type,
            "metrics": metrics,
            "sec_names": sec_names,
            "sec_ids": sec_ids,
            "start_date": start_date,
            "end_date": end_date,
            "addl_options": addl_options,
            "raise_perm_errors": raise_perm_errors,
        }

        if metrics_chunk_size is None and securities_chunk_size is None:
            # no chunking
            data = self._get_security_metrics_helper(**params)  # type: ignore
            return pd.json_normalize(data, max_level=normalize_level)

        self._validate_chunking_options(
            addl_options=addl_options,
            metrics=metrics,
            sec_names=sec_names,
            sec_ids=sec_ids,
            metrics_chunk_size=metrics_chunk_size,
            securities_chunk_size=securities_chunk_size,
        )

        dfs: list[pd.DataFrame] = []

        if metrics_chunk_size is not None:
            for chunk in batch_post_payload(rows=list(metrics), batch_size=metrics_chunk_size):
                params["metrics"] = chunk
                data = self._get_security_metrics_helper(**params)  # type: ignore
                df = pd.json_normalize(data, max_level=normalize_level)

                # when we chunk by metrics, we may be missing some becuase the secapi doesnt return it if its None for all records
                for m in metrics:
                    if m not in df:
                        df[m] = None
                dfs.append(df)

        elif securities_chunk_size is not None:
            if sec_names:
                for chunk in batch_post_payload(rows=list(sec_names), batch_size=securities_chunk_size):
                    params["sec_names"] = chunk
                    data = self._get_security_metrics_helper(**params)  # type: ignore
                    dfs.append(pd.json_normalize(data, max_level=normalize_level))
            elif sec_ids:
                for chunk in batch_post_payload(rows=list(sec_ids), batch_size=securities_chunk_size):
                    params["sec_ids"] = chunk
                    data = self._get_security_metrics_helper(**params)  # type: ignore
                    dfs.append(pd.json_normalize(data, max_level=normalize_level))

        # the groupbys below squashes
        # eff1 id1 m1=NAN m2=x
        # eff2 id1 m1=Y  m2=NAN
        # into
        # eff1 id1 m1=Y m2=x
        # also:
        # for chunked, we return a consistent sort order of id, eff_ts
        return (
            pd.concat(dfs)
            .groupby(["eff_ts", "id"])
            .last()
            .reset_index()
            .sort_values(["id", "eff_ts"])
            .reset_index()
            .drop("index", axis=1)
        )
