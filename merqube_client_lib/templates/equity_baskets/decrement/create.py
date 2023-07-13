"""
Create an equity basket index
"""
import logging
from typing import Final, cast

from merqube_client_lib.api_client.merqube_client import MerqubeAPIClient
from merqube_client_lib.exceptions import IndexNotFound
from merqube_client_lib.logging import get_module_logger
from merqube_client_lib.templates.equity_baskets.schema import ClientDecrementConfig
from merqube_client_lib.templates.equity_baskets.util import create_index, load_template
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
            t.spec
            and t.spec.index_class_args
            and (cs := t.spec.index_class_args.get("spec").get("portfolios", {}).get("constituents"))  # type: ignore
            and len(cs) == 1
            and cs[0]["identifier"] == ric
        ):
            return t.name
    return None


def _validate_dec_params(client: MerqubeAPIClient, tr_name: str, index_info: ClientDecrementConfig) -> None:
    """
    Validates that the decrement parameters are valid based on the underlying TR
    """

    # end_date = min(base_date, start_date)?
    mets = client.get_security_metrics(sec_type="index", sec_names=[tr_name], metrics="total_return")


def create(config_file_path: str, prod_run: bool = False) -> CreateReturn:
    """
    Creates a new Equity Basket with multiple entries
    This class does not handle Corax.
    """
    client, template, index_info, inner_spec = load_template(
        template_name="DECREMENT_TEMPLATE_VERSION_1", config_file_path=config_file_path, model=ClientDecrementConfig
    )

    index_info = cast(ClientDecrementConfig, index_info)

    if not (tr_name := _tr_exists(client, index_info.ric)):
        raise IndexNotFound(f"Could not find a TR on {index_info.ric}. Please contact MerQube support.")

    _validate_dec_params(client, tr_name, index_info)

    # set the metric to the TR metric
    template.plot_metric = inner_spec.get("output_metric", (getattr(template, "plot_metric", "price_return")))

    # ???
    # inner_spec["output_metric"] = underlying_secapi_metric
    # inner_spec["metric"] = underlying_secapi_metric  # the decrement index looks up the returns of the tr via this
    # inner_spec["underlying_level_type"] = "total_return"
    inner_spec["underlying_ticker"] = tr_name
    inner_spec["day_count_convention"] = index_info.day_count_convention
    inner_spec["fee"] = {"fee_value": index_info.fee_value, "fee_type": index_info.fee_type.value}

    post_template, ident_ppost = create_index(
        client=client, template=template, index_info=index_info, inner_spec=inner_spec, prod_run=prod_run
    )

    return CreateReturn(post_template, ident_ppost)
