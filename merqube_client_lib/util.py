"""
Misc helper utilities
"""
import datetime
import json
import os
from typing import Any, cast

import pandas as pd


def batch_post_payload(rows: list[Any], batch_size: int) -> list[list[Any]]:
    """
    returns a list of sublists of size <= batch_size
    used widely for POSTing large payloads to e.g., secapi
    If you have veryy large payloads, you may want to consider doing this math virtually rather than recopying.
    """
    # If rows is `None` or is an empty list, it doesn't need to be a list of sublist at all
    if rows is None or len(rows) == 0:
        return []
    if len(rows) > batch_size:
        n = batch_size
        return [rows[i * n : (i + 1) * n] for i in range((len(rows) + n - 1) // n)]
    return [rows]


def freezable_now_ts(tz: str = "UTC") -> pd.Timestamp:
    """
    Builds pd.Timestamp.now out of a datetime.datetime so it can be frozen in unit tests; pandas Timestamps are not compatible with freeze_gun
    """
    dt = datetime.datetime.utcnow()
    return cast(pd.Timestamp, pd.Timestamp(dt, tz="UTC").tz_convert(tz))


def freezable_now_iso(tz: str = "UTC") -> str:
    """returns localized timestamp as iso string"""
    return cast(str, freezable_now_ts(tz).isoformat())


def freezable_utcnow_ts() -> pd.Timestamp:
    """returns unlocalized utc timestamp"""
    return freezable_now_ts().tz_localize(None)


def freezable_utcnow_iso() -> str:
    """returns unlocalized utc timestamp as iso string"""
    return cast(str, freezable_utcnow_ts().isoformat())


def get_token() -> str:
    """
    Gets the users token from the env var
    """
    if not (api_key := os.environ.get("MERQ_API_KEY")):
        raise ValueError("MERQ_API_KEY not set")
    return api_key


def pydantic_to_dict(
    pydantic_obj: Any, exclude_none: bool = True, exclude_defaults: bool = True, exclude_unset: bool = True
) -> dict[str, Any]:
    """
    helper function to convert pydantic objects to dictionaries
    you would think .dict() would work - but that can still contain objects such as Enums,
    which are not json serializable
    """
    return cast(
        dict[str, Any],
        json.loads(
            pydantic_obj.json(exclude_none=exclude_none, exclude_defaults=exclude_defaults, exclude_unset=exclude_unset)
        ),
    )
