"""
Combined API Client for all merqube APIs
"""
from functools import partial
from typing import Any, cast

import pandas as pd
from cachetools import LRUCache, cached

from merqube_client_lib.api_client import base
from merqube_client_lib.constants import MERQ_CLIENT_PREFIX
from merqube_client_lib.pydantic_types import EquityBasketPortfolio, IdentifierUUIDPost
from merqube_client_lib.pydantic_types import IndexDefinitionPatchPutGet as Index
from merqube_client_lib.pydantic_types import Provider
from merqube_client_lib.session import MerqubeAPISession
from merqube_client_lib.util import pydantic_to_dict


class MerqubeAPIClient(base._IndexAPIClient, base._SecAPIClient):  # noqa
    """
    Combined API Client for indexapi + secapi, for methods that do not pertain to a particular index
    (general queries, CRUD of indices, etc)
    For a client pertaining to a specific existing index, use MerqubeAPIClientSingleIndex
    """

    def __init__(self, *args: Any, req_id_prefix: str = MERQ_CLIENT_PREFIX, **kwargs: Any) -> None:
        super().__init__(*args, req_id_prefix=req_id_prefix, **kwargs)

    def create_identifier(
        self, provider: Provider, identifier_post: IdentifierUUIDPost | dict[str, Any]
    ) -> dict[str, Any]:
        """
        Create a new identifier (in MerQubes system - this does NOT talk to the provider)
        """
        name = (
            payload := (
                pydantic_to_dict(identifier_post)
                if isinstance(identifier_post, IdentifierUUIDPost)
                else identifier_post
            )
        )["name"]
        linked_name = payload["index_name"]

        results = self.session.get_collection(f"/identifier/{provider.value}?names={name}")
        if len(results) == 0:
            return cast(dict[str, Any], self.session.post(f"/identifier/{provider.value}", json=payload).json())

        if (exis_name := results[0]["index_name"]) == linked_name:
            return {"status": "already exists for this index name"}
        raise ValueError(f"Identifier {name} already exists for a different index name ({exis_name})")


class MerqubeAPIClientSingleIndex(MerqubeAPIClient):
    """
    Class that contains methods that deal with a single index
    Instantiate with an index name ("name" field in the index manifest) and indicate if it is a realtime index
    """

    def __init__(
        self,
        index_name: str,
        is_intraday: bool = False,
        *args: Any,
        req_id_prefix: str = MERQ_CLIENT_PREFIX,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, req_id_prefix=req_id_prefix, **kwargs)

        self._model: Index = self.get_index_model(index_name=index_name)
        self._index_id = self._model.id
        self._is_intraday = is_intraday
        self._index_name = index_name

        # intraday model has a nasty type of [None | Intraday | Bool ..]
        self._has_intraday = self._model.intraday is not None and (
            (isinstance(self._model.intraday, bool) and self._model.intraday) or self._model.intraday.enabled is True
        )

        # get the security id for this index
        self._sec_id = self.session.get_collection_single(f"/security/index?name={index_name}")["id"]
        self._intra_sec_id = (
            self.session.get_collection_single(f"/security/intraday_index?name={index_name}")["id"]
            if self._has_intraday
            else None
        )

        # partials over id methods; partials preserve types
        self.get_manifest = partial(self.get_index_manifest, index_id=self._index_id)
        self.post_model_from_existing = partial(self.index_post_model_from_existing, index_id=self._index_id)
        self.get_last_run_state = partial(self.get_last_index_run_state, index_id=self._index_id)
        self.lock = partial(self.lock_index, index_id=self._index_id)
        self.unlock = partial(self.unlock_index, index_id=self._index_id)
        self.partial_update = partial(self.patch_index, index_id=self._index_id)

    @property
    def model(self) -> Index:
        return self._model

    @property
    def id(self) -> str:
        return self._index_id

    @property
    def name(self) -> str:
        return self._index_name

    @property
    def is_intraday(self) -> bool:
        return self._is_intraday

    def get_metrics(
        self,
        metrics: list[str],
        use_intraday_metrics: bool = False,
        start_date: pd.Timestamp | None = None,
        end_date: pd.Timestamp | None = None,
    ) -> pd.DataFrame:
        """
        Get a list of metrics for this index
        Some indices are both end of day and intraday - use the flag to query for intraday metrics
        """
        return self.get_security_metrics(
            sec_type="intraday_index" if use_intraday_metrics else "index",
            sec_ids=[cast(str, self._intra_sec_id) if use_intraday_metrics else self._sec_id],
            metrics=metrics,
            start_date=start_date,
            end_date=end_date,
        )

    def get_returns(
        self,
        returns_metric: str = "price_return",
        use_intraday_metrics: bool = False,
        start_date: pd.Timestamp | None = None,
        end_date: pd.Timestamp | None = None,
    ) -> pd.DataFrame:
        """
        Get returns for this index
        Some indices are both end of day and intraday - use the flag to query for intraday metrics
        """
        if use_intraday_metrics and not self._has_intraday:
            raise ValueError("This index is not an intraday index")

        return self.get_metrics(
            metrics=[returns_metric],
            use_intraday_metrics=use_intraday_metrics,
            start_date=start_date,
            end_date=end_date,
        )

    def get_portfolio(self) -> list[dict[str, Any]]:
        """
        Get list of portfolios for specified index id
        Each entry in the array has a date, and it's the portfolio that was active on that (rebalance) date
        """
        return self.session.get_collection(f"/index/{self._index_id}/portfolio")

    def get_portfolio_allocations(self) -> list[dict[str, Any]]:
        """
        Get list of portfolio allocations for specified index id
        This is a view of how the portfolio has changed over time
        """
        return self.session.get_collection(f"/index/{self._index_id}/portfolio_allocations")

    def get_target_portfolio(
        self, start_date: pd.Timestamp | None = None, end_date: pd.Timestamp | None = None
    ) -> list[dict[str, Any]]:
        """
        Some indices allow the customer to set a target portfolio (e.g., equity baskets) and a target date
        this returns those target_portfolios
        sometime after the date of each, a get on /portfolio may return the target portfolio (but in some cases it may not be possible to achieve the exact target)
        """
        opts = {}
        if start_date is not None:
            opts["start_date"] = start_date.isoformat()

        if end_date is not None:
            opts["end_date"] = end_date.isoformat()

        return self.session.get_collection(f"/index/{self._index_id}/target_portfolio", options=opts)

    def get_caps(self) -> list[dict[str, Any]]:
        """
        Get list of caps for specified index id (only applies to buffer indices)
        """
        return self.session.get_collection(f"/index/{self._index_id}/caps")

    def get_stats(self) -> list[dict[str, Any]]:
        """
        Get stats, which are historical returns over different time periods, of the index
        """
        return self.session.get_collection(f"/index/{self._index_id}/stats")

    def get_data_collections(self) -> list[dict[str, Any]]:
        """
        Get list of data collections for specified index id

        Data Collections are a system for retrieving data on a daily basis after calculations have been performed.  After data has been disseminated for public usage on various providers like Reuters, Bloomberg, etc, clients may opt-in to receive this data directly from MerQube.  We may also provide intermediate data that is not directly disseminated which might be useful for clients.

        This is not available for all indices
        """
        return self.session.get_collection(f"/index/{self._index_id}/data_collections")

    def replace_portfolio(self, target_portfolio: dict[str, Any] | EquityBasketPortfolio) -> dict[str, Any]:
        """
        set the open portfolio for a given day. see the base class docs for more info
        """
        tp = (
            pydantic_to_dict(target_portfolio)
            if isinstance(target_portfolio, EquityBasketPortfolio)
            else target_portfolio
        )
        return self.replace_target_portfolio(index_id=self._index_id, target_portfolio=tp)


client_cache: LRUCache = LRUCache(maxsize=256)  # type: ignore


@cached(cache=client_cache)
def get_client(
    index_name: str | None = None,
    is_intraday: bool = False,
    user_session: MerqubeAPISession | None = None,
    token: str | None = None,
    **session_kwargs: Any,
) -> MerqubeAPIClient | MerqubeAPIClientSingleIndex:
    """
    Cached; returns a Merqube client (or SingleClient if provided an index name) for token
    """
    return (
        MerqubeAPIClientSingleIndex(
            index_name=index_name, is_intraday=is_intraday, user_session=user_session, token=token, **session_kwargs
        )
        if index_name
        else MerqubeAPIClient(user_session=user_session, token=token, **session_kwargs)
    )
