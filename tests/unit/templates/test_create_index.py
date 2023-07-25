import json
import os
import tempfile
from typing import Any
from unittest.mock import MagicMock, call

import pytest
from click.testing import CliRunner

from merqube_client_lib.pydantic_types import RunState
from merqube_client_lib.pydantic_types import RunStateStatus as RSS
from merqube_client_lib.templates.equity_baskets.bin.create_index import main
from merqube_client_lib.templates.equity_baskets.util import EquityBasketIndexCreator


@pytest.mark.parametrize("prod_run", [True, False])
@pytest.mark.parametrize("poll", [0, 10])
def test_click_cli(prod_run, poll, monkeypatch):
    dec = MagicMock()
    mult = MagicMock()
    ss = MagicMock()

    class DecCl(EquityBasketIndexCreator):
        create = dec

    class MultCl(EquityBasketIndexCreator):
        create = mult

    class SsCl(EquityBasketIndexCreator):
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
def test_poll(seq, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda x: None)
    count = 0

    class Cl(EquityBasketIndexCreator):
        def create(self, config: dict[str, Any], prod_run: bool, poll: int):
            pass

    class FakeClient:
        def get_last_index_run_state(self, index_id: str) -> RunState:
            nonlocal count
            if count >= len(seq):
                return RunState(status=seq[-1], error=None)

            res = seq[count]
            count += 1
            return RunState(status=res, error=None)

    if seq[-1] == RSS.SUCCEEDED:
        Cl()._poll(client=FakeClient(), new_id="asdf", poll=5)
    else:
        with pytest.raises(RuntimeError):
            Cl()._poll(client=FakeClient(), new_id="asdf", poll=5)
