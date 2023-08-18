import json
import os
import tempfile
from copy import deepcopy
from unittest.mock import MagicMock, call

import pytest
from click.testing import CliRunner

from merqube_client_lib.pydantic_types import (
    IdentifierUUIDPost,
    IndexDefinitionPost,
    Provider,
    RunState,
)
from merqube_client_lib.pydantic_types import RunStateStatus as RSS
from merqube_client_lib.templates.equity_baskets.bin.create_index import main
from merqube_client_lib.templates.equity_baskets.creators import (
    DecrementIndexCreator,
    MultiEBIndexCreator,
    SSTRIndexCreator,
)
from merqube_client_lib.util import pydantic_to_dict

here = os.path.dirname(os.path.abspath(__file__))


def SS(ticker: str | None = None):
    return {
        "base_date": "2010-01-04",
        "bbg_ticker": ticker,
        "currency": "USD",
        "description": "COST TR Index",
        "email_list": ["tommy@merqube.com"],
        "name": "MQU_COST_TR",
        "namespace": "merqubetr",
        "run_hour": 18,
        "run_minute": 0,
        "timezone": "US/Eastern",
        "title": "COST TR Index",
        "ric": "COST.OQ",
    }


def EB():
    return {
        "base_date": "2015-01-05",
        "base_value": 1000,
        "constituents_csv_path": os.path.join(here, "../fixtures/portfolios_initial.csv"),
        "level_overrides_csv_path": os.path.join(here, "../fixtures/level_overrides.csv"),
        "corporate_actions": {"reinvest_dividends": True},
        "currency": "USD",
        "description": "multiple equity basket tp",
        "email_list": ["tommy@merqube.com"],
        "name": "test_multi_basket",
        "namespace": "test",
        "run_hour": 18,
        "run_minute": 0,
        "timezone": "US/Eastern",
        "title": "multiple equity basket tp",
    }


@pytest.mark.parametrize("prod", [True, False])
@pytest.mark.parametrize(
    "ticker, tickobj", [(None, None), ("ticker", {"index_name": "foo", "ticker": "test", "name": "asdf"})]
)
def test_create_index_options(prod, ticker, tickobj, templated_ss):
    conf = SS(ticker)

    class FakeRes:
        def json(self):
            return {"post_template": templated_ss, "bbg_ident_template": tickobj}

    fake_post = MagicMock(return_value=FakeRes())
    fake_create_ident = MagicMock(return_value={"id": "abcd"})
    fake_create_index = MagicMock(return_value={"id": "1234"})
    fake_ports = MagicMock()

    cl = SSTRIndexCreator()
    cl._client.session.post = fake_post
    cl._client.create_identifier = fake_create_ident
    cl._client.create_index = fake_create_index
    cl._client.replace_target_portfolio = fake_ports

    cl.create(config=conf, poll=0, prod_run=prod)

    assert fake_ports.call_args_list == []  # only for multi eb
    assert fake_post.call_args_list == [call("/helper/index-template/sstr", json=conf)]

    if not prod:
        assert fake_create_ident.call_args_list == []
        assert fake_create_index.call_args_list == []
    else:
        assert (
            fake_create_ident.call_args_list == []
            if ticker is None
            else [[call(provider=Provider.bloomberg, identifier_post=IdentifierUUIDPost.parse_obj(tickobj))]]
        )
        assert fake_create_index.call_args_list == [call(index_def=IndexDefinitionPost.parse_obj(templated_ss))]


def test_multi_eb_parsing(templated_mult, templated_mult_ports):
    class FakeRes:
        def json(self):
            return {"post_template": templated_mult, "target_ports": templated_mult_ports}

    fake_post = MagicMock(return_value=FakeRes())
    fake_create_ident = MagicMock()
    fake_create_index = MagicMock(return_value={"id": "1234"})
    fake_ports = MagicMock()

    cl = MultiEBIndexCreator()
    cl._client.session.post = fake_post
    cl._client.create_identifier = fake_create_ident
    cl._client.create_index = fake_create_index
    cl._client.replace_target_portfolio = fake_ports

    conf = EB()

    cl.create(config=conf, poll=0, prod_run=True)

    exp = deepcopy(conf)

    exp["constituents"] = [
        {"date": "2022-03-11", "identifier": "AAPL.OQ", "quantity": -0.2512355, "security_type": "EQUITY"},
        {"date": "2022-03-11", "identifier": "AMZN.OQ", "quantity": -0.28782633781297995, "security_type": "EQUITY"},
        {"date": "2022-03-11", "identifier": "GOOG.OQ", "quantity": 0.78687756527879, "security_type": "EQUITY"},
        {"date": "2022-03-11", "identifier": "A.N", "quantity": 0.8687756527878999, "security_type": "EQUITY"},
        {"date": "2022-03-11", "identifier": "USD", "quantity": 60.0, "security_type": "CASH"},
    ]
    assert "constituents_csv_path" not in exp
    exp["level_overrides"] = [{"date": "2022-03-18", "level": 1364.344, "comment": "Level override test"}]
    assert "level_overrides_csv_path" not in exp

    # assert fake_create.call_args_list == [call(config=exp, prod_run=False, poll=0)]
    assert fake_post.call_args_list == [call("/helper/index-template/multi_eb", json=conf)]
    assert fake_create_ident.call_args_list == []
    assert fake_create_index.call_args_list == [call(index_def=IndexDefinitionPost.parse_obj(templated_mult))]
    assert [
        pydantic_to_dict(x) for x in fake_ports.call_args_list[0].kwargs["target_portfolio"]
    ] == templated_mult_ports


@pytest.mark.parametrize("prod_run", [True, False])
@pytest.mark.parametrize("poll", [0, 10])
def test_click_cli(prod_run, poll, monkeypatch):
    dec = MagicMock()
    mult = MagicMock()
    ss = MagicMock()

    class DecCl(DecrementIndexCreator):
        create = dec

    class MultCl(MultiEBIndexCreator):
        create = mult

    class SsCl(SSTRIndexCreator):
        create = ss

    monkeypatch.setattr("merqube_client_lib.templates.equity_baskets.bin.create_index.DC", DecCl)
    monkeypatch.setattr("merqube_client_lib.templates.equity_baskets.bin.create_index.MEB", MultCl)
    monkeypatch.setattr("merqube_client_lib.templates.equity_baskets.bin.create_index.SSTR", SsCl)

    cli = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        with open((pth := os.path.join(tmpdir, "config.json")), "w") as f:
            f.write(json.dumps({"my": "config"}))

        expected_call = call(config={"my": "config"}, poll=poll, prod_run=prod_run)

        args = ["--index-type", "decrement", "--config-file-path", pth, "--poll", poll]
        if prod_run:
            args.append("--prod-run")

        result = cli.invoke(main, args)
        assert result.exit_code == 0, (result.output, result.exception, result.stderr_bytes)

        assert dec.call_args_list == [expected_call]
        assert mult.call_args_list == []
        assert ss.call_args_list == []

        # run a mult

        args = ["--index-type", "multiple_equity_basket", "--config-file-path", pth, "--poll", poll]
        if prod_run:
            args.append("--prod-run")

        result = cli.invoke(main, args)
        assert result.exit_code == 0, (result.output, result.exception, result.stderr_bytes)

        assert dec.call_args_list == [expected_call]
        assert mult.call_args_list == [expected_call]
        assert ss.call_args_list == []

        # run an ss twice
        args = ["--index-type", "single_stock_total_return", "--config-file-path", pth, "--poll", poll]
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


@pytest.mark.parametrize("cls", [DecrementIndexCreator, MultiEBIndexCreator, SSTRIndexCreator])
@pytest.mark.parametrize(
    "seq",
    [
        [RSS.PENDING_CREATION],
        [RSS.RUNNING],
        [RSS.PENDING_CREATION, RSS.FAILED],
        [RSS.PENDING_CREATION, RSS.RUNNING],
        [RSS.PENDING_CREATION, RSS.RUNNING, RSS.FAILED],
        # good
        [RSS.PENDING_CREATION, RSS.RUNNING, RSS.SUCCEEDED],
        [RSS.PENDING_CREATION, RSS.SUCCEEDED],  # could happen if run takes <60s
        [RSS.SUCCEEDED],
    ],
)
def test_poll(cls, seq, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda x: None)
    count = 0

    class FakeClient:
        def get_last_index_run_state(self, index_id: str) -> RunState:
            nonlocal count
            if count >= len(seq):
                return RunState(status=seq[-1], error=None)

            res = seq[count]
            count += 1
            return RunState(status=res, error=None)

    cr = cls()
    cr._client = FakeClient()

    if seq[-1] == RSS.SUCCEEDED:
        cr._poll(new_id="asdf", poll=5)
    else:
        with pytest.raises(RuntimeError):
            cr._poll(new_id="asdf", poll=5)
