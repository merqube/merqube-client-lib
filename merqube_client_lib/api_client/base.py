"""
Base class for all Merqube API Clients
"""
from typing import Any, Iterable, Optional

# import like this so monkeypatch works as expected
from merqube_client_lib import session
from merqube_client_lib.types import ManifestList


class MerqubeApiClientBase:
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
    ) -> ManifestList:
        """
        common function to /security metrics and definitions
        """
        options: dict[str, str | list[str]] = {}

        for qo, v in (query_options or {}).items():
            if v is not None:
                options[qo] = v if isinstance(v, str) else ",".join(v)

        return self.session.get_collection(url=url, options=options)
