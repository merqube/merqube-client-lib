"""
Tests for utilities
"""

import pandas as pd
import pytest
from freezegun import freeze_time

from merqube_client_lib.util import (
    batch_post_payload,
    freezable_now_iso,
    freezable_now_ts,
    freezable_utcnow_iso,
    freezable_utcnow_ts,
)


def test_batch_post_payload():
    """tests batch_post_payload"""
    assert batch_post_payload([], 1) == []
    payload = list(i for i in range(1, 11))
    assert batch_post_payload(payload, 1) == [[1], [2], [3], [4], [5], [6], [7], [8], [9], [10]]
    assert batch_post_payload(payload, 2) == [[1, 2], [3, 4], [5, 6], [7, 8], [9, 10]]
    assert batch_post_payload(payload, 3) == [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10]]
    assert batch_post_payload(payload, 4) == [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10]]
    assert batch_post_payload(payload, 5) == [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]]
    assert batch_post_payload(payload, 6) == [[1, 2, 3, 4, 5, 6], [7, 8, 9, 10]]
    assert batch_post_payload(payload, 7) == [[1, 2, 3, 4, 5, 6, 7], [8, 9, 10]]
    assert batch_post_payload(payload, 8) == [[1, 2, 3, 4, 5, 6, 7, 8], [9, 10]]
    assert batch_post_payload(payload, 9) == [[1, 2, 3, 4, 5, 6, 7, 8, 9], [10]]
    assert batch_post_payload(payload, 10) == [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]]
    assert batch_post_payload(payload, 100) == [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]]
    assert batch_post_payload(list(i for i in range(1, 18)), 5) == [
        [1, 2, 3, 4, 5],
        [6, 7, 8, 9, 10],
        [11, 12, 13, 14, 15],
        [16, 17],
    ]


@freeze_time("2023-06-06T06:06:09")
@pytest.mark.parametrize(
    "tz, expec, expec_iso",
    [
        (None, pd.Timestamp("2023-06-06 06:06:09"), "2023-06-06T06:06:09"),
        ("US/Eastern", pd.Timestamp("2023-06-06 02:06:09-0400", tz="US/Eastern"), "2023-06-06T02:06:09-04:00"),
        ("Europe/London", pd.Timestamp("2023-06-06 07:06:09+0100", tz="Europe/London"), "2023-06-06T07:06:09+01:00"),
    ],
)
def test_freezable_now(tz, expec, expec_iso):
    assert freezable_now_ts(tz=tz) == expec
    assert freezable_now_iso(tz=tz) == expec_iso


@freeze_time("2023-06-06T06:06:09")
def test_utc_now():
    assert freezable_utcnow_ts() == pd.Timestamp("2023-06-06T06:06:09")
    assert freezable_utcnow_iso() == "2023-06-06T06:06:09"
