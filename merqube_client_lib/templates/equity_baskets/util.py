import json
import logging
from typing import Any, cast

import pandas as pd
import pytz

from merqube_client_lib.api_client.merqube_client import MerqubeAPIClient
from merqube_client_lib.logging import get_module_logger
from merqube_client_lib.pydantic_types import (
    BasketPosition,
    EquityBasketPortfolio,
    IdentifierUUIDRef,
    IndexDefinitionPatchPutGet,
    IndexDefinitionPost,
    IntradayPublishConfigBloombergTarget,
    IntradayPublishConfigTarget,
    PortfolioUom,
    Provider,
    RicEquityPosition,
    Stage,
)

SPEC_KEYS = ["base_date"]
TOP_LEVEL = ["namespace", "name", "title", "base_date"]
MISC = ["apikey", "run_hour", "run_minute"]
INFO_REQUIRED = TOP_LEVEL + SPEC_KEYS + MISC
OPTIONAL = "timezone"


logger = get_module_logger(__name__, level=logging.DEBUG)


def inline_to_tp(index_model: IndexDefinitionPatchPutGet) -> list[tuple[str, EquityBasketPortfolio]]:
    """Convert the inline portfolio to a list of target portfolios"""

    target_portfolios = []

    assert index_model.spec and index_model.spec.index_class_args and index_model.spec.index_class_args.get("spec")
    portfolio = index_model.spec.index_class_args["spec"]["portfolios"]
    uom = PortfolioUom.UNITS if portfolio["quantity_type"] == "SHARES" else PortfolioUom.WEIGHT
    id_type = portfolio["identifier_type"]

    # see how nany TP values we need
    dates = set()
    for constituent in (const := portfolio["constituents"]):
        dates.add(constituent["date"])

    for date in sorted(dates):
        positions: list[BasketPosition | RicEquityPosition] = []
        for constituent in const:
            sec_type = constituent["security_type"]
            pos_class = RicEquityPosition if sec_type == "EQUITY" else BasketPosition

            if constituent["date"] != date:
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

        target_port_val = EquityBasketPortfolio(timestamp=date, unit_of_measure=uom, positions=positions)

        EquityBasketPortfolio.parse_obj(target_port_val)  # validate
        target_portfolios.append((date, target_port_val))

    return target_portfolios


def read_file(filename: str) -> list[Any]:
    """reads portfolio/overrides files"""
    return list(pd.read_csv(filename, float_precision="round_trip").to_dict(orient="index").values())


def log_index(index: IndexDefinitionPost) -> None:
    """
    Logs the resulting index
    """
    json_formatted_str = json.dumps(json.loads(index.json(exclude_none=True)), indent=4)
    logger.info("Index spec: \n" + json_formatted_str)


def get_index_info(config_file_path: str, required_fields: list[str]) -> dict[str, Any]:
    """
    load index specific info from config file + validate the data
    """
    index_info = cast(dict[str, Any], json.load(open(config_file_path, "r")))

    for k in required_fields:
        if k not in index_info:
            raise ValueError(f"Missing key {k} in index info")

    try:
        for k in ["base_date"]:
            pd.Timestamp(index_info[k])
    except ValueError as e:
        raise ValueError(
            "{k} must be a valid date. If the index should run at a certain time of day UTC, that should be part of the ISO8601 formatted first_run_date"
        ) from e

    if (tz := index_info.get("timezone")) and tz not in pytz.all_timezones:
        raise ValueError("Invalid timezone string: {tz}")

    return index_info


def load_template(
    template_name: str, config_file_path: str, type_required_specific_fields: list[str]
) -> tuple[MerqubeAPIClient, IndexDefinitionPost, dict[str, Any], dict[str, Any]]:
    """
    Loads a template index model to edit and then create a new index from
    """
    index_info = get_index_info(
        config_file_path=config_file_path, required_fields=type_required_specific_fields + INFO_REQUIRED
    )
    token = index_info.get("apikey")

    client = MerqubeAPIClient(token=token)
    template = client.index_post_model_from_existing(template_name)

    assert template.spec and template.spec.index_class_args and template.spec.index_class_args.get("spec")
    inner_spec = template.spec.index_class_args["spec"]

    return client, template, index_info, inner_spec


def configure_index(template: IndexDefinitionPost, index_info: dict[str, Any], inner_spec: dict[str, Any]) -> None:
    """
    set up the index from index info
    """
    for k in TOP_LEVEL:
        setattr(template, k, index_info[k])

    inner_spec["index_id"] = index_info["name"]
    for k in SPEC_KEYS:
        inner_spec[k] = index_info[k]

    # set the start date at which this will start running
    assert template.run_configuration and template.run_configuration.schedule

    # set runtime
    # make sure to produce the last EOD value immediately on create
    today = pd.Timestamp.now().date() - pd.Timedelta(days=2)
    template.run_configuration.schedule.schedule_start = pd.Timestamp(
        year=today.year,
        month=today.month,
        day=today.day,
        hour=index_info["run_hour"],
        minute=index_info["run_minute"],
        second=0,
    ).isoformat()
    template.run_configuration.tzinfo = index_info.get("timezone", "US/Eastern")

    template.identifiers = (
        [IdentifierUUIDRef(name=bbgt, provider=Provider.bloomberg)] if (bbgt := index_info.get("bbg_ticker")) else []
    )

    template.stage = Stage.prod
    template.run_configuration.job_enabled = True

    if index_info.get("is_intraday"):
        assert template.intraday and template.intraday.publish_config and template.intraday.publish_config
        template.intraday.enabled = True
        if index_info.get("bbg_ticker"):
            assert template.intraday.publish_config.__root__
            cast(list[IntradayPublishConfigTarget], template.intraday.publish_config.__root__["price_return"]).append(
                IntradayPublishConfigTarget(
                    __root__=IntradayPublishConfigBloombergTarget(target="bloomberg", active_time_ranges=None)
                )
            )


def create_index(
    client: MerqubeAPIClient,
    template: IndexDefinitionPost,
    index_info: dict[str, Any],
    inner_spec: dict[str, Any],
    prod_run: bool,
) -> IndexDefinitionPost:
    configure_index(template=template, index_info=index_info, inner_spec=inner_spec)

    log_index(template)

    if prod_run:
        res = client.create_index(index_def=template)
        logger.info(f"Created index: {res}")

    return template
