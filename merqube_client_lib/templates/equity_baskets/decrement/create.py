"""
Create an equity basket index
"""
import logging
import os
import tempfile
from typing import Any, cast

import boto3
import pandas as pd

from merqube_client_lib.exceptions import APIError
from merqube_client_lib.logging import get_module_logger
from merqube_client_lib.templates.equity_baskets.schema import ClientDecrementConfig
from merqube_client_lib.templates.equity_baskets.util import create_index, load_template
from merqube_client_lib.types import CreateReturn, Records

logger = get_module_logger(__name__, level=logging.DEBUG)


def _download_tr_map(tdir: str) -> str:
    """broken out for ease of unit testing"""
    s3 = boto3.client("s3")
    s3.download_file("merq-api-assets", "tr_indices.csv", (pth := os.path.join(tdir, "tr.csv")))
    return pth


def _get_trs(tr: str | None = None) -> Records:
    """
    Returns the list of all MerQube TRs decrements can be on
    """
    with tempfile.TemporaryDirectory() as tdir:
        trs = pd.read_csv(_download_tr_map(tdir))

    if trs.empty:
        raise ValueError("No TRs found")

    trs = trs.sort_values(by=["underlying_ric"])

    if not tr:
        return cast(Records, trs.to_dict(orient="records"))

    row = trs[trs["index_name"] == tr]
    if row.empty:
        raise ValueError(f"{tr} is not a valid TR")

    return cast(Records, row.to_dict(orient="records"))


def create(config: dict[str, Any], prod_run: bool = False) -> CreateReturn:
    """
    Creates a new Equity Basket with multiple entries
    This class does not handle Corax.
    """
    client, template, index_info, inner_spec = load_template(
        template_name="DECREMENT_TEMPLATE_VERSION_1", config=config, model=ClientDecrementConfig
    )

    index_info = cast(ClientDecrementConfig, index_info)

    uin = index_info.underlying_index_name
    if index_info.client_owned_underlying:
        # check that the underlying index exists
        logger.info(f"Checking that the underlying index {uin} exists")
        try:
            client.get_index_model(index_name=uin)
        except APIError:
            raise ValueError(f"{uin} is not a valid index or you are not permissioned for it")

        underlying_secapi_metric = "price_return"
    else:
        logger.info(f"Checking that the underlying index {uin} is a permissioned MerQube provided TR")
        tr = _get_trs(uin)[0]
        underlying_secapi_metric = tr["metric"]

    # set the metric to the TR metric
    template.plot_metric = inner_spec.get("output_metric", (getattr(template, "plot_metric", "price_return")))

    inner_spec["metric"] = underlying_secapi_metric  # the decrement index looks up the returns of the tr via this
    inner_spec["underlying_ticker"] = uin
    inner_spec["day_count_convention"] = index_info.day_count_convention
    inner_spec["fee"] = {"fee_value": index_info.fee_value, "fee_type": index_info.fee_type.value}

    post_template, ident_ppost = create_index(
        client=client, template=template, index_info=index_info, inner_spec=inner_spec, prod_run=prod_run
    )

    return CreateReturn(post_template, ident_ppost)
