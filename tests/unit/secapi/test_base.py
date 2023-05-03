"""
Tests for _ClientBase
"""
from unittest.mock import MagicMock, call

import pytest

from merqube_client_lib.secapi import client


@pytest.mark.parametrize(
    "options, expected", [(None, {}), ({"foo": "bar"}, {"foo": "bar"}), ({"names": ["n1", "n2"]}, {"names": "n1,n2"})]
)
def test_options(options, expected):
    ch = MagicMock(return_value=[{"foo1": "bar1"}, {"foo2": "bar2"}])

    class mock_session:
        def __init__(self):
            self.get_collection = ch

    cl = client._ClientBase(session=mock_session())

    assert cl._collection_helper(url="test_url", query_options=options) == [{"foo1": "bar1"}, {"foo2": "bar2"}]
    assert ch.call_args_list == [call(url="test_url", options=expected)]


@pytest.mark.parametrize(
    "params, func, should_work",
    [
        ({"sec_type": "nooo"}, "_validate_secapi_type", False),
        ({"sec_type": "sectype1"}, "_validate_secapi_type", True),
        ({"sec_type": "sectype1"}, "_validate_single", False),
        ({"sec_type": "sectype1", "sec_id": None}, "_validate_single", False),
        ({"sec_type": "sectype1", "sec_id": "1234"}, "_validate_single", True),
        ({"sec_type": "sectype1", "sec_id": "1234", "sec_name": "myname"}, "_validate_single", False),
        ({"sec_type": "sectype1", "sec_id": None, "sec_name": "myname"}, "_validate_single", True),
    ],
)
def test_arg_validation(params, func, should_work):
    ch = MagicMock(return_value=[{"name": "sectype1"}, {"name": "sectype2"}])

    class mock_session:
        def __init__(self):
            self.get_collection = ch

    cl = client._ClientBase(session=mock_session())

    if should_work:
        getattr(cl, func)(**params)
    else:
        with pytest.raises(AssertionError):
            getattr(cl, func)(**params)
