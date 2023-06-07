"""
Unit test helpers
"""
import json
import os
import tempfile
from copy import deepcopy
from unittest.mock import MagicMock

import pytest

from tests.conftest import mock_secapi


def eb_test(
    func, config, bbg_ticker, expected, expected_bbg_post, template, monkeypatch, email_list=None, intraday=False
):
    """shared helper used for all equity basket tests"""
    mock_secapi(
        monkeypatch,
        method_name_function_map={},
        session_func_map={"get_collection_single": MagicMock(return_value=template)},
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        with open((fpath := os.path.join(tmpdir, "test.json")), "w") as f:
            conf = deepcopy(config)
            conf["bbg_ticker"] = bbg_ticker
            if intraday:
                conf["is_intraday"] = intraday

            if email_list:
                conf["email_list"] = email_list

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

        with pytest.raises(ValueError):
            func(config_file_path=fpath)
