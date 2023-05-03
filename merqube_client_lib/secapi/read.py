"""
NOTE: this module is not meant to be used by the client directly. 
The SecAPI client is meant to be used instead.

This implements underlying functions that are used by the SecAPI client.
"""
from typing import Iterable, Optional, Union

from merqube_client_lib.secapi.util import (
    collection_helper,
    sec_validator_multiple,
    sec_validator_single,
)
from merqube_client_lib.session import MerqubeAPISession
from merqube_client_lib.types.secapi import (
    AddlSecapiOptions,
    MappingTable,
    SecapiMetricDefinition,
)


@sec_validator_single
def get_metrics_for_security(
    *,
    sec_type: str,
    session: MerqubeAPISession,
    sec_id: str | None = None,
    sec_name: str | None = None,
) -> list[SecapiMetricDefinition]:
    """
    Get the list of metrics that are currently available for a security
    Can query by id or name
    """
    return session.get_collection(
        f"/security/{sec_type}/{sec_id}/metrics" if sec_id else f"/security/{sec_type}/metrics?name={sec_name}"
    )


@sec_validator_multiple
def get_security_definitions_mapping_table(
    sec_type: str,
    session: MerqubeAPISession,
    sec_names: Optional[str | Iterable[str]] = None,
    sec_ids: Optional[str | Iterable[str]] = None,
    addl_options: Optional[AddlSecapiOptions] = None,
) -> MappingTable:
    """
    Lists defined (and permissioned) securities for a type.
    Returns a mapping table; either name -> id, or id -> name
    """
    query_options: dict[str, Union[str | None, Optional[Iterable[str]]]] = {"names": sec_names, "ids": sec_ids}
    if addl_options is not None:
        query_options.update(addl_options)

    rec_data = collection_helper(
        url=f"/security/{sec_type}",
        query_options=query_options,
        session=session,
    )

    return {c["id"]: c["name"] for c in rec_data} if sec_ids else {c["name"]: c["id"] for c in rec_data}
