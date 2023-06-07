import os
import tempfile
from unittest.mock import MagicMock, call

import pytest
from click.testing import CliRunner

from merqube_client_lib.templates.equity_baskets.create_index import main


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
            f.write("mocked")

        expected_call = call(config_file_path=pth, prod_run=prod_run)

        args = ["--index-type", "decrement", "--config-file-path", pth]
        if prod_run:
            args.append("--prod-run")

        result = cli.invoke(main, args)
        assert result.exit_code == 0, (result.output, result.exception, result.stderr_bytes)

        assert dec.call_args_list == [expected_call]
        assert mult.call_args_list == []
        assert ss.call_args_list == []

        # run a mult

        args = ["--index-type", "multi_basket_no_corax", "--config-file-path", pth]
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
