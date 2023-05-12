"""
Tests for utilities
"""
from merqube_client_lib.util import batch_post_payload


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
