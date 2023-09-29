import pytest
from click.testing import CliRunner

from merqube_client_lib.templates.bin.get_example import main


@pytest.mark.parametrize("itype", ["decrement", "multiple_equity_basket", "single_stock_total_return"])
def test_click_cli(itype):
    cli = CliRunner()

    args = ["--index-type", itype]
    result = cli.invoke(main, args, catch_exceptions=False)
    assert result.exit_code == 0, (result.output, result.exception, result.stderr_bytes)


def test_cli_fail():
    cli: CliRunner = CliRunner()
    result = cli.invoke(main, ["--index-type", "noooo"], catch_exceptions=False)
    assert result.exit_code == 2
