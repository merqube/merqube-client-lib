"""
Unit test helpers
"""
import json
import os
import tempfile
from copy import deepcopy
from unittest.mock import MagicMock

import pytest

from merqube_client_lib.exceptions import APIError
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

    with tempfile.TemporaryDirectory() as tmpdir:
        with open((fpath := os.path.join(tmpdir, "test.json")), "w") as f:
            conf = deepcopy(config)
            conf["bbg_ticker"] = bbg_ticker
            if intraday:
                conf["is_intraday"] = intraday

            if email_list:
                conf["email_list"] = email_list

            if client_owned_underlying is not None:
                conf["client_owned_underlying"] = client_owned_underlying

            f.write(json.dumps(conf))

        template, bbg_post = func(config_file_path=fpath)
        assert (act := json.loads(template.json(exclude_none=True))) == expected, act
        if expected_bbg_post is None:
            assert bbg_post is None
        else:
            assert json.loads(bbg_post.json(exclude_none=True)) == expected_bbg_post


def eb_test_bad(func, config, template, monkeypatch):
    """shared helper used for all equity basket tests"""
    mock_secapi(
        monkeypatch,
        method_name_function_map={},
        session_func_map={"get_collection_single": MagicMock(return_value=template)},
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        with open((fpath := os.path.join(tmpdir, "test.json")), "w") as f:
            f.write(json.dumps(config))

        with pytest.raises(ValueError) as e:
            func(config_file_path=fpath)

        return e.exconly()
