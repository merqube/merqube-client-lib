"""
Create an equity basket index
"""
import logging
from typing import Any, Final, cast

import pandas as pd

from merqube_client_lib.api_client.merqube_client import MerqubeAPIClient
from merqube_client_lib.constants import PRICE_RETURN, TOTAL_RETURN
from merqube_client_lib.exceptions import IndexNotFound
from merqube_client_lib.logging import get_module_logger
from merqube_client_lib.templates.equity_baskets.schema import ClientDecrementConfig
from merqube_client_lib.templates.equity_baskets.util import EquityBasketIndexCreator
from merqube_client_lib.types import CreateReturn

logger = get_module_logger(__name__, level=logging.DEBUG)


MERQ_PROVIDED_TR_NS: Final = "merqubetr"


def _tr_exists(client: MerqubeAPIClient, ric: str) -> str | None:
    """
    returns the name of the TR index on `ric` if it exists, else None
    """
    logger.info(f"Checking that a permissioned underlying TR on {ric} exists")
    for t in client.get_indices_in_namespace(namespace=MERQ_PROVIDED_TR_NS):
        if (
            t.run_configuration
            and t.run_configuration.job_enabled is True
            and t.spec
            and t.spec.index_class_args
            and (cs := t.spec.index_class_args.get("spec").get("portfolios", {}).get("constituents"))  # type: ignore
            and len(cs) == 1
            and cs[0]["identifier"] == ric
        ):
            return cast(str, t.name)
    return None


def _validate_dec_params(client: MerqubeAPIClient, index_info: ClientDecrementConfig) -> str:
    """
    Validates that the decrement parameters are valid, and based on a valid underlying TR
    """
    pr_check_date = index_info.start_date or index_info.base_date

    if index_info.start_date and index_info.start_date > index_info.base_date:
        raise ValueError("The start date of the decrement index, if specified, must be before the base date")

    if not (tr_name := _tr_exists(client, index_info.ric)):
        raise IndexNotFound(f"Could not find a TR on {index_info.ric}. Please contact MerQube support.")

    # validate that the start date of the decrement index is after the start date of the TR
    mets = client.get_security_metrics(
        sec_type="index", sec_names=[tr_name], metrics=PRICE_RETURN, end_date=pd.Timestamp(pr_check_date)
    )
    if mets.empty:
        raise ValueError(f"There are no returns for the tr {tr_name} before {pr_check_date}")

    return tr_name


class DecrementIndexCreator(EquityBasketIndexCreator):
    """create a decrement index on top of a SSTR"""

    @property
    def output_metric(self) -> str:
        return TOTAL_RETURN

    def create(self, config: dict[str, Any], prod_run: bool = False, poll: int = 0) -> CreateReturn:
        """
        Creates a new Equity Basket with multiple entries
        This class does not handle Corax.
        """
        client, template, index_info, inner_spec = self._load_template(
            template_name="DECREMENT_TEMPLATE_VERSION_1", config=config, model=ClientDecrementConfig
        )

        index_info = cast(ClientDecrementConfig, index_info)

        tr_name = _validate_dec_params(client, index_info)

        inner_spec["holiday_spec"]["calendar_identifiers"] = [f"MQI:{tr_name}"]

        inner_spec["start_date"] = index_info.start_date or index_info.base_date

        # the decrement index looks up the returns of the tr via this
        inner_spec["underlying_ticker"] = tr_name
        inner_spec["day_count_convention"] = index_info.day_count_convention
        inner_spec["fee"] = {"fee_value": index_info.fee_value, "fee_type": index_info.fee_type.value}

        post_template, ident_ppost = self._create_index(
            client=client, template=template, index_info=index_info, inner_spec=inner_spec, prod_run=prod_run, poll=poll
        )

        return CreateReturn(post_template, ident_ppost)
