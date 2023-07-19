import json
import os
import tempfile
from copy import deepcopy
from unittest.mock import ANY, MagicMock, call

import pytest
from click.testing import CliRunner

from merqube_client_lib.pydantic_types import (
    IdentifierUUIDPost,
    IndexDefinitionPost,
    Provider,
)
from merqube_client_lib.templates.equity_baskets.create_index import main
from merqube_client_lib.templates.equity_baskets.multiple_equity_basket.base import (
    inline_to_tp,
)
from merqube_client_lib.templates.equity_baskets.multiple_equity_basket.create import (
    create_index,
)
from merqube_client_lib.templates.equity_baskets.schema import ClientIndexConfigBase


@pytest.mark.parametrize("prod_run", [True, False])
def test_click_cli(prod_run, monkeypatch):
    dec = MagicMock()
    mult = MagicMock()
    ss = MagicMock()

    monkeypatch.setattr("merqube_client_lib.templates.equity_baskets.create_index.dec_index", dec)
    monkeypatch.setattr("merqube_client_lib.templates.equity_baskets.create_index.mult_index", mult)
    monkeypatch.setattr("merqube_client_lib.templates.equity_baskets.create_index.ss_index", ss)

    cli = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        with open((pth := os.path.join(tmpdir, "config.json")), "w") as f:
            f.write(json.dumps({"my": "config"}))

        expected_call = call(config={"my": "config"}, prod_run=prod_run)

        args = ["--index-type", "decrement", "--config-file-path", pth]
        if prod_run:
            args.append("--prod-run")

        result = cli.invoke(main, args)
        assert result.exit_code == 0, (result.output, result.exception, result.stderr_bytes)

        assert dec.call_args_list == [expected_call]
        assert mult.call_args_list == []
        assert ss.call_args_list == []

        # run a mult

        args = ["--index-type", "multiple_equity_basket", "--config-file-path", pth]
        if prod_run:
            args.append("--prod-run")

        result = cli.invoke(main, args)
        assert result.exit_code == 0, (result.output, result.exception, result.stderr_bytes)

        assert dec.call_args_list == [expected_call]
        assert mult.call_args_list == [expected_call]
        assert ss.call_args_list == []

        # run an ss twice
        args = ["--index-type", "single_stock_total_return", "--config-file-path", pth]
        if prod_run:
            args.append("--prod-run")

        result = cli.invoke(main, args)
        assert result.exit_code == 0, (result.output, result.exception, result.stderr_bytes)
        result = cli.invoke(main, args)
        assert result.exit_code == 0, (result.output, result.exception, result.stderr_bytes)

        assert dec.call_args_list == [expected_call]
        assert mult.call_args_list == [expected_call]
        assert ss.call_args_list == [expected_call, expected_call]


def test_cli_fail():
    cli: CliRunner = CliRunner()
    result = cli.invoke(main, ["--index-type", "noooo"])
    assert result.exit_code == 2

    result = cli.invoke(main, ["--index-type", "decrement"])
    assert result.exit_code == 2

    result = cli.invoke(main, ["--index-type", "decrement", "--config-file-path", "noooot/exist"])
    assert result.exit_code == 1

    with tempfile.TemporaryDirectory() as tmpdir:
        with open((pth := os.path.join(tmpdir, "config.json")), "w") as f:
            f.write("nooooootajson")

        result = cli.invoke(main, ["--index-type", "decrement", "--config-file-path", pth])
        assert result.exit_code == 1


iinfo = {
    "base_value": 100,
    "namespace": "testns",
    "name": "testname",
    "title": "testtitle",
    "base_date": "2022-01-01",
    "description": "testdesc",
    "holiday_calendar": None,
    "run_hour": 16,
    "run_minute": 0,
}

iinfo = ClientIndexConfigBase.parse_obj(iinfo)


def _get_client():
    ident = MagicMock()
    index = MagicMock()
    target = MagicMock()

    class FakeClient:
        create_identifier = ident
        create_index = index
        replace_target_portfolio = target

    return FakeClient(), ident, index, target


def test_prod_run(v1_multi):
    manifest = deepcopy(v1_multi)
    del manifest["id"]
    del manifest["status"]
    ind = IndexDefinitionPost.parse_obj(manifest)

    client, ident, index, target = _get_client()
    create_index(
        client=client,
        template=ind,
        index_info=iinfo,
        inner_spec={},
        prod_run=True,
    )

    assert ident.call_args_list == []
    assert index.call_args_list == [call(index_def=ANY)]
    assert target.call_args_list == []


def test_prod_run_ticker(v1_multi):
    manifest = deepcopy(v1_multi)
    del manifest["id"]
    del manifest["status"]
    ind = IndexDefinitionPost.parse_obj(manifest)

    inf = deepcopy(iinfo)
    inf.bbg_ticker = "TEST"

    client, ident, index, target = _get_client()
    create_index(
        client=client,
        template=ind,
        index_info=inf,
        inner_spec={},
        prod_run=True,
    )

    assert ident.call_args_list == [
        call(
            provider=Provider.bloomberg,
            identifier_post=IdentifierUUIDPost(index_name="testname", name="TEST", namespace="testns", ticker="TEST"),
        )
    ]
    assert index.call_args_list == [call(index_def=ANY)]
    assert target.call_args_list == []


def test_prod_run_ticker_tp(v1_multi):
    manifest = deepcopy(v1_multi)
    del manifest["id"]
    del manifest["status"]
    ind = IndexDefinitionPost.parse_obj(manifest)
    ind.spec.index_class_args["spec"]["portfolios"]["constituents"] = [
        {"date": "2023-06-12", "identifier": "AA.N", "quantity": 1, "security_type": "EQUITY"},
        {"date": "2023-06-12", "identifier": "AAPL.OQ", "quantity": 2, "security_type": "EQUITY"},
        {"date": "2023-06-13", "identifier": "AA.N", "quantity": 2, "security_type": "EQUITY"},
        {"date": "2023-06-13", "identifier": "USD", "quantity": 100000000, "security_type": "CASH"},
    ]

    inf = deepcopy(iinfo)
    inf.bbg_ticker = "TEST"

    client, ident, index, target = _get_client()
    create_index(
        client=client,
        template=ind,
        index_info=inf,
        inner_spec={},
        initial_target_portfolios=inline_to_tp(ind.spec.index_class_args["spec"]["portfolios"]),
        prod_run=True,
    )

    assert ident.call_args_list == [
        call(
            provider=Provider.bloomberg,
            identifier_post=IdentifierUUIDPost(index_name="testname", name="TEST", namespace="testns", ticker="TEST"),
        )
    ]
    assert index.call_args_list == [call(index_def=ANY)]
    assert target.call_args_list == [
        call(
            index_id=ANY,
            target_portfolio={
                "positions": [
                    {"amount": 1.0, "asset_type": "EQUITY", "identifier": "AA.N", "identifier_type": "RIC"},
                    {"amount": 2.0, "asset_type": "EQUITY", "identifier": "AAPL.OQ", "identifier_type": "RIC"},
                ],
                "timestamp": "2023-06-12T00:00:00",
                "unit_of_measure": "SHARES",
            },
        ),
        call(
            index_id=ANY,
            target_portfolio={
                "positions": [
                    {"amount": 2.0, "asset_type": "EQUITY", "identifier": "AA.N", "identifier_type": "RIC"},
                    {
                        "amount": 100000000.0,
                        "asset_type": "CASH",
                        "identifier": "USD",
                        "identifier_type": "CURRENCY_CODE",
                    },
                ],
                "timestamp": "2023-06-13T00:00:00",
                "unit_of_measure": "SHARES",
            },
        ),
    ]
