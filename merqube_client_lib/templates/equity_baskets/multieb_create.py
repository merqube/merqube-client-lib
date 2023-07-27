"""
Create an equity basket index
"""
from typing import Any, cast

import pandas as pd

from merqube_client_lib.constants import PRICE_RETURN
from merqube_client_lib.logging import get_module_logger
from merqube_client_lib.pydantic_types import (
    BasketPosition,
    EquityBasketPortfolio,
    PortfolioUom,
    RicEquityPosition,
)
from merqube_client_lib.templates.equity_baskets.schema import (
    ClientMultiEquityBasketConfig,
)
from merqube_client_lib.templates.equity_baskets.util import (
    EquityBasketIndexCreator,
    read_file,
)
from merqube_client_lib.types import CreateReturn, TargetPortfoliosDates

logger = get_module_logger(__name__)


class MultiEquityBasketIndexCreator(EquityBasketIndexCreator):
    """creates a generic basket of equities"""

    @property
    def output_metric(self) -> str:
        return PRICE_RETURN

    def _get_constituents(
        self,
        constituents_csv_path: str,
        base_date: str | pd.Timestamp | None = None,
        base_value: float | None = None,
        add_initial_cash_position: bool = False,
    ) -> list[dict[str, Any]]:
        """read and validate constituents file"""
        constituents = read_file(constituents_csv_path)

        if add_initial_cash_position:
            if not base_date or not base_value:
                raise ValueError("base_date and base_value must be set if add_initial_cash_position is True")

            if pd.Timestamp(base_date) >= pd.Timestamp(min(c["date"] for c in constituents)):
                raise ValueError("base_date should be set to a date at least one day before the first portfolio date")

            constituents += cast(
                dict[str, Any],
                [
                    {
                        "date": base_date,
                        "identifier": "USD",
                        "quantity": base_value,
                        "security_type": "CASH",
                    }
                ],
            )

        return constituents

    def _inline_to_tp(self, portfolio: dict[str, Any]) -> TargetPortfoliosDates:
        """
        Convert the inline portfolio to a list of target portfolios
        """

        target_portfolios: TargetPortfoliosDates = []

        uom = PortfolioUom.SHARES if portfolio["quantity_type"] == "SHARES" else PortfolioUom.WEIGHT
        id_type = portfolio["identifier_type"]

        # see how nany TP values we need
        dates = set()
        for constituent in (const := portfolio["constituents"]):
            dates.add(pd.Timestamp(constituent["date"]))

        for date in sorted(dates):
            positions: list[BasketPosition | RicEquityPosition] = []
            for constituent in const:
                sec_type = constituent["security_type"]
                pos_class = RicEquityPosition if sec_type == "EQUITY" else BasketPosition

                if pd.Timestamp(constituent["date"]) != date:
                    continue  # will get picked up in another target portfolio

                positions.append(
                    pos_class(
                        asset_type=constituent["security_type"],
                        identifier=constituent["identifier"],
                        amount=constituent["quantity"],
                        # this is only at the top level of inline; but its wrong for the cash position (in TP it is CURRENCY_CODE)
                        identifier_type="CURRENCY_CODE" if sec_type == "CASH" else id_type,
                    )
                )

            target_port_val = EquityBasketPortfolio(timestamp=date, unit_of_measure=uom, positions=positions)  # type: ignore

            EquityBasketPortfolio.parse_obj(target_port_val)  # validate
            target_portfolios.append((date, target_port_val))

        return target_portfolios

    def create(self, config: dict[str, Any], prod_run: bool = False, poll: int = 0) -> CreateReturn:
        """
        Creates a new Equity Basket with multiple entries
        """
        client, template, index_info, inner_spec = self._load_template(
            template_name="EQUITY_BASKET_TEMPLATE_V1",
            config=config,
            model=ClientMultiEquityBasketConfig,
        )

        index_info = cast(ClientMultiEquityBasketConfig, index_info)

        if index_info.corporate_actions.reinvest_dividends:
            # unfortunately, this class has all corax on except for dividend reinvestment -
            # the standard case for this client tool is to turn dividend reinvestment on;
            # we cannot just delete the whole corporate_actions dict
            inner_spec["corporate_actions"] = {
                "dividend": {"deduct_tax": False, "reinvest_day": "PREV_DAY", "reinvest_strategy": "IN_INDEX"}
            }

        const = self._get_constituents(
            constituents_csv_path=index_info.constituents_csv_path,
            base_date=cast(pd.Timestamp, index_info.base_date),
            base_value=index_info.base_value,
            add_initial_cash_position=True,
        )

        ports = {
            "constituents": const,
            "date_type": "EFFECTIVE",
            "identifier_type": "RIC",
            "quantity_type": "SHARES",
            "specification_type": "API",
        }

        target_portfolios = self._inline_to_tp(ports)

        inner_spec["portfolios"]["specification_type"] = "API"
        inner_spec["portfolios"]["constituents"] = []

        if pth := index_info.level_overrides_csv_path:
            inner_spec["level_overrides"] = read_file(pth)

        post_template, ident = self._create_index(
            client=client,
            template=template,
            index_info=index_info,
            inner_spec=inner_spec,
            prod_run=prod_run,
            initial_target_portfolios=target_portfolios,
            poll=poll,
        )

        return CreateReturn(template=post_template, ident=ident, initial_target_ports=target_portfolios)
