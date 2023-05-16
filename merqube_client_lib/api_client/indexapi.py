"""
Client library for Indexapi
"""
from typing import cast

from merqube_client_lib.api_client.base import MerqubeApiClientBase
from merqube_client_lib.pydantic_types import IndexDefinitionPatchPutGet as Index
from merqube_client_lib.types import Manifest


class IndexAPIClient(MerqubeApiClientBase):
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

    def create_index(self, index_def: Index) -> dict[str, str]:
        """
        Create an index
        Returns a dictionary containing the id of the index and its related securities (index, intraday_index)

        TODO: examples and index templates to be added to this repo.
        """
        return cast(dict[str, str], self.session.post("/index", json=index_def.dict()).json())

    def update_index(self, index_id: str, index_def: Index) -> None:
        """
        Update (full object replacement) an index
        """
        self.session.put(f"/index/{index_id}", json=index_def.dict())

    def patch_index(self, index_id: str, index_updates: Manifest) -> None:
        """
        Patch an index - index_updates is a partial index manifest
        """
        self.session.patch(f"/index/{index_id}", json=index_updates)

    def delete_index(self, index_id: str) -> None:
        """
        Delete an index
        """
        self.session.delete(f"/index/{index_id}")
