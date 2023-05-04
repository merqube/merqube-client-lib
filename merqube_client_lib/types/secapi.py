"""
Secapi types
"""
from typing import Any

from typing_extensions import NotRequired, TypedDict


class SecapiMetricDefinition(TypedDict):
    """The definition of a metric"""

    name: str
    description: NotRequired[str]
    data_type: NotRequired[str]
    object_schema: NotRequired[dict[str, Any]]


SecAPIRecordsResponse = list[dict[str, Any]]
AddlSecapiOptions = dict[str, Any]
MappingTable = dict[str, str]
