"""
Misc helper utilities
"""
from typing import Any


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
