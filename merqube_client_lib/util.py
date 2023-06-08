"""
Misc helper utilities
"""
import datetime
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


def freezable_now(tz: str = "UTC", no_tzinfo_iso: bool = False) -> pd.Timestamp | str:
    """
    Builds pd.Timestamp.now out of a datetime.datetime so it can be frozen in unit tests
    """
    dt = datetime.datetime.utcnow()
    ts = pd.Timestamp(dt, tz="UTC").tz_convert(tz)
    if not no_tzinfo_iso:
        return cast(pd.Timestamp, ts)
    return ts.tz_localize(None).isoformat()  # pyright: ignore


def freezable_utcnow(no_tzinfo_iso: bool = False) -> pd.Timestamp | str:
    """
    Builds pd.Timestamp.utcnow out of a datetime.datetime so it can be frozen in unit tests
    """
    return freezable_now(no_tzinfo_iso=no_tzinfo_iso)


def get_token() -> str:
    """
    Gets the users token from the env var
    """
    if not (api_key := os.environ.get("MERQ_API_KEY")):
        raise ValueError("MERQ_API_KEY not set")
    return api_key
