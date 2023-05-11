"""
Combined API Client for all merqube APIs
"""
from typing import Any

from cachetools import LRUCache, cached

from merqube_client_lib.api_client.indexapi import IndexAPIClient
from merqube_client_lib.secapi.client import SecAPIClient
from merqube_client_lib.session import MerqubeAPISession


class MerqubeAPIClient(IndexAPIClient, SecAPIClient):
    """combined Merqube client"""


client_cache: LRUCache = LRUCache(maxsize=256)  # type: ignore


@cached(cache=client_cache)
def get_client(
    user_session: MerqubeAPISession | None = None, token: str | None = None, **session_kwargs: Any
) -> MerqubeAPIClient:
    """
    Cached; returns a Merqube client for token
    """
    return MerqubeAPIClient(user_session=user_session, token=token, **session_kwargs)
