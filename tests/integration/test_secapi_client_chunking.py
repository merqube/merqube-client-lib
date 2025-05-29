"""
Tests for get_security_metrics when chunking (splitting a call that would result in a massive result set into multiple calls)
"""

from functools import partial

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from merqube_client_lib.api_client.merqube_client import get_client
from tests.unit.fixtures.gsm_fixtures import TEST_IDS_NE, TEST_METRICS_NE, TEST_NAMES_NE

CHUNK_TESTS = [(1), (2), (3), (4), (5), (6)]


def gsm_call():
    public = get_client()

    sm = partial(
        public.get_security_metrics,
        sec_type="index",
        start_date=pd.Timestamp("2023-04-27"),
        end_date=pd.Timestamp("2023-05-03"),
        addl_options={"as_of": "2023-05-04T12:00:00"},  # result set is frozen
    )

    return sm


@pytest.mark.parametrize("chunk_size", CHUNK_TESTS)
@pytest.mark.parametrize("which_sec_type", [("ids"), ("names")])
def test_single_security_mutliple_metrics_chunked(
    which_sec_type,
    chunk_size,
):
    """
    tests chunking a single security that has a lot of metrics
    """
    sm = gsm_call()

    kwargs = {"metrics": TEST_METRICS_NE}
    if which_sec_type == "ids":
        kwargs["sec_ids"] = TEST_IDS_NE[0]
    else:
        kwargs["sec_names"] = TEST_NAMES_NE[0]

    single_mult_no_chunk = sm(**kwargs)
    assert single_mult_no_chunk.columns.tolist() == [
        "daily_return",
        "eff_ts",
        "id",
        "metricdoesnotexist",
        "name",
        "price_return",
        "total_return",
    ]

    chunked = sm(
        **kwargs,
        metrics_chunk_size=chunk_size,
    )
    assert_frame_equal(left=single_mult_no_chunk, right=chunked, check_like=True)


@pytest.mark.parametrize("chunk_size", CHUNK_TESTS)
@pytest.mark.parametrize("which_sec_type", [("ids"), ("names")])
def test_multi_ids_single_metrics_chunked(
    which_sec_type,
    chunk_size,
):
    """
    tests chunking by ids when there is one metric
    """
    sm = gsm_call()
    kwargs = {"metrics": "price_return"}
    if which_sec_type == "ids":
        kwargs["sec_ids"] = TEST_IDS_NE
    else:
        kwargs["sec_names"] = TEST_NAMES_NE

    mult_single = sm(**kwargs)
    assert len(mult_single) == 15
    assert mult_single.columns.tolist() == ["eff_ts", "id", "name", "price_return"]
    assert mult_single.index.equals(pd.RangeIndex(start=0, stop=15, step=1))

    chunked = sm(
        **kwargs,
        securities_chunk_size=chunk_size,
    )

    # row order is not gauranteed to be preserved when chunking
    mult_single = mult_single.sort_values(["id", "eff_ts"]).reset_index().drop("index", axis=1)
    assert_frame_equal(left=mult_single, right=chunked, check_like=True)


@pytest.mark.parametrize("chunk_size", CHUNK_TESTS)
@pytest.mark.parametrize("which_sec_type", [("ids"), ("names")])
def test_multi_ids_multi_metrics_chunked(
    which_sec_type,
    chunk_size,
):
    """
    tests chunking by ids with multiple metrics for each
    """
    sm = gsm_call()

    kwargs = {"metrics": TEST_METRICS_NE}
    if which_sec_type == "ids":
        kwargs["sec_ids"] = TEST_IDS_NE
    else:
        kwargs["sec_names"] = TEST_NAMES_NE

    mult_mult = sm(**kwargs)
    assert len(mult_mult) == 15
    assert mult_mult.columns.tolist() == [
        "daily_return",
        "eff_ts",
        "id",
        "metricdoesnotexist",
        "name",
        "price_return",
        "total_return",
    ]

    # row order is not gauranteed to be preserved when chunking
    # if we apply this sort to the gsm without chunking, it would be
    mult_mult = mult_mult.sort_values(["id", "eff_ts"]).reset_index().drop("index", axis=1)

    chunked = sm(
        **kwargs,
        securities_chunk_size=chunk_size,
    )
    # chunking by ids should not change the result set
    assert_frame_equal(left=mult_mult, right=chunked, check_like=True)

    chunked = sm(
        **kwargs,
        metrics_chunk_size=chunk_size,
    )
    # chunking by metrics should not change the result set
    assert_frame_equal(left=mult_mult, right=chunked, check_like=True)
