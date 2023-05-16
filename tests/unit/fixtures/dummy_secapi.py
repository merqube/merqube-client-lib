from unittest.mock import MagicMock

from cachetools import LRUCache, cached

from merqube_client_lib.api_client.merqube_client import MerqubeAPIClient

client_cache = LRUCache(maxsize=1)


class DummyAPIClient(MerqubeAPIClient):
    """few addl methods"""

    def get_futures_contracts_from_secapi(self):
        return ["originals"]


def _get_session():
    return MagicMock()


@cached(cache=client_cache)
def get_client():
    return DummyAPIClient(user_session=_get_session())
