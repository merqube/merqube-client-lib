"""
Client library for Indexapi
"""
from merqube_client_lib.api_client.base import MerqubeApiClientBase
from merqube_client_lib.types import Manifest


class IndexAPIClient(MerqubeApiClientBase):
    """
    Indexapi Client
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
