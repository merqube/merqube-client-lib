"""
Unit test helpers
"""
from copy import deepcopy
from unittest.mock import MagicMock

import pytest

from merqube_client_lib.exceptions import APIError
from merqube_client_lib.util import pydantic_to_dict
from tests.conftest import mock_secapi


def eb_test(
    func,
    config,
    bbg_ticker,
    expected,
    expected_bbg_post,
    template,
    monkeypatch,
    email_list=None,
    intraday=False,
    client_owned_underlying=None,
    expected_target_portfolios=None,
    corax_conf=None,
    base_value=None,
):
    """shared helper used for all equity basket tests"""

    call_count = 0

    def _get_collection_single(*args, **kwargs):
        nonlocal call_count
        if not client_owned_underlying:
            return template

        call_count += 1
        if call_count == 1:
            return template

        if client_owned_underlying == "missing":
            raise APIError()
        return client_owned_underlying

    mock_secapi(
        monkeypatch,
        method_name_function_map={},
        session_func_map={"get_collection_single": _get_collection_single},
    )

    conf = deepcopy(config)
    conf["bbg_ticker"] = bbg_ticker
    if intraday:
        conf["is_intraday"] = intraday

    if email_list:
        conf["email_list"] = email_list

    if client_owned_underlying is not None:
        conf["client_owned_underlying"] = bool(client_owned_underlying)

    if corax_conf is not None:
        conf["corporate_actions"] = corax_conf

    if base_value is not None:
        conf["base_value"] = base_value
        expected["spec"]["index_class_args"]["spec"]["base_val"] = float(base_value)

    cr = func(config=conf)

    # assert the index template
    assert pydantic_to_dict(cr.template) == expected

    # assert the bbg template (if applicable)
    if expected_bbg_post is None:
        assert cr.ident is None
    else:
        assert pydantic_to_dict(cr.ident) == expected_bbg_post

    # assert target portfolios (if applicable)
    if expected_target_portfolios is None:
        assert cr.initial_target_ports is None
    else:
        assert [(x, pydantic_to_dict(y)) for (x, y) in cr.initial_target_ports] == expected_target_portfolios


def eb_test_bad(func, config, template, monkeypatch):
    """shared helper used for all equity basket tests"""
    mock_secapi(
        monkeypatch,
        method_name_function_map={},
        session_func_map={"get_collection_single": MagicMock(return_value=template)},
    )

    with pytest.raises(ValueError) as e:
        func(config=config)

    return e.exconly()
