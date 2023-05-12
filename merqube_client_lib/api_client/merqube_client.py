"""
Combined API Client for all merqube APIs
"""
from typing import Any

import pandas as pd
from cachetools import LRUCache, cached

from merqube_client_lib.api_client.base import MerqubeApiClientBase
from merqube_client_lib.api_client.indexapi import IndexAPIClient
from merqube_client_lib.pydantic_types import IndexDefinitionPatchPutGet as Index
from merqube_client_lib.secapi.client import SecAPIClient
from merqube_client_lib.session import MerqubeAPISession
from merqube_client_lib.types import Manifest


class MerqubeAPIClient(IndexAPIClient, SecAPIClient):
    """
    Combined API Client for indexapi + secapi, for methods that do not pertain to a particular index
    (general queries, CRUD of indices, etc)
    For a client pertaining to a specific existing index, use MerqubeAPIClientSingleIndex
    """


class MerqubeAPIClientSingleIndex(MerqubeApiClientBase):
    """
    Class that contains methods that deal with a single index
    """

    def __init__(self, index_name: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        res = self.session.get_collection_single(f"/index?names={index_name}")
        self.index_id = res["id"]

    def get_index_manifest(self) -> Manifest:
        """
        Get index definition for specified index id
        """
        return self.session.get_json(f"/index/{self.index_id}")

    def get_index_model(self) -> Index:
        """
        Get index model for specified index id
        """
        return Index.parse_obj(self.get_index_manifest())

    def get_returns(
        self,
        returns_metric: str = "price_return",
        start_date: pd.Timestamp | None = None,
        end_date: pd.Timestamp | None = None,
    ) -> pd.DataFrame:
        raise NotImplementedError((returns_metric, start_date, end_date))

    def get_metrics(
        self,
        metrics: list[str],
        start_date: pd.Timestamp | None = None,
        end_date: pd.Timestamp | None = None,
    ) -> pd.DataFrame:
        raise NotImplementedError((metrics, start_date, end_date))

    def get_portfolio(self) -> list[dict[str, Any]]:
        """
        Get list of portfolios for specified index id
        Each entry in the array has a date, and it's the portfolio that was active on that (rebalance) date
        """
        return self.session.get_collection(f"/index/{self.index_id}/portfolio")

    def get_portfolio_allocations(self) -> list[dict[str, Any]]:
        """
        Get list of portfolio allocations for specified index id
        This is a view of how the portfolio has changed over time
        """
        return self.session.get_collection(f"/index/{self.index_id}/portfolio_allocations")

    def get_target_portfolio(self) -> list[dict[str, Any]]:
        """
        Some indices allow the customer to set a target portfolio (e.g., equity baskets) and a target date
        this returns those target_portfolios
        sometime after the date of each, a get on /portfolio may return the target portfolio (but in some cases it may not be possible to achieve the exact target)
        """
        return self.session.get_collection(f"/index/{self.index_id}/target_portfolio")

    def get_caps(self) -> list[dict[str, Any]]:
        """
        Get list of caps for specified index id (only applies to buffer indices)
        """
        return self.session.get_collection(f"/index/{self.index_id}/caps")

    def get_stats(self) -> list[dict[str, Any]]:
        """
        Get stats, which are historical returns over different time periods, of the index
        """
        return self.session.get_collection(f"/index/{self.index_id}/stats")

    def get_data_collections(self) -> list[dict[str, Any]]:
        """
        Get list of data collections for specified index id

        Data Collections are a system for retrieving data on a daily basis after calculations have been performed.  After data has been disseminated for public usage on various providers like Reuters, Bloomberg, etc, clients may opt-in to receive this data directly from MerQube.  We may also provide intermediate data that is not directly disseminated which might be useful for clients.

        This is not available for all indices
        """
        return self.session.get_collection(f"/index/{self.index_id}/data_collections")


client_cache: LRUCache = LRUCache(maxsize=256)  # type: ignore


@cached(cache=client_cache)
def get_client(
    user_session: MerqubeAPISession | None = None, token: str | None = None, **session_kwargs: Any
) -> MerqubeAPIClient:
    """
    Cached; returns a Merqube client for token
    """
    return MerqubeAPIClient(user_session=user_session, token=token, **session_kwargs)
