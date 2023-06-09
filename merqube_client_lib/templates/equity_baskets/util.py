import json
import logging
from copy import deepcopy
from typing import Any, cast

import pandas as pd
import pytz
from pydantic.error_wrappers import ValidationError

from merqube_client_lib.api_client.merqube_client import MerqubeAPIClient
from merqube_client_lib.logging import get_module_logger
from merqube_client_lib.pydantic_types import (
    BasketPosition,
    EquityBasketPortfolio,
    HolidayCalendarSpec,
    IdentifierUUIDPost,
    IdentifierUUIDRef,
    IndexDefinitionPatchPutGet,
    IndexDefinitionPost,
    IndexReport,
    IntradayPublishConfigBloombergTarget,
    IntradayPublishConfigTarget,
    PortfolioUom,
    Provider,
    RicEquityPosition,
    Stage,
)
from merqube_client_lib.util import freezable_utcnow, get_token

SPEC_KEYS = ["base_date"]
DATE_KEYS = ["base_date"]

# TODO: use jsonschema instead
TOP_LEVEL = ["namespace", "name", "title", "base_date", "description"]
MISC = ["run_hour", "run_minute"]
REQUIRED_BASE_FIELDS = TOP_LEVEL + SPEC_KEYS + MISC

OPTIONAL_BASE_FIELDS = [
    "addl_comments",
    "bbg_ticker",
    "currency",
    "is_intraday",
    "timezone",
    "holiday_calendar",
    "email_list",
]


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


def get_index_info(
    config_file_path: str, type_specific_req_fields: list[str] = [], type_specific_opt_fields: list[str] = []
) -> dict[str, Any]:
    """
    load index specific info from config file + validate the data
    """
    index_info = cast(dict[str, Any], json.load(open(config_file_path, "r")))

    for k in (req := REQUIRED_BASE_FIELDS + type_specific_req_fields):
        if k not in index_info:
            raise ValueError(f"Missing required key {k} in index info")

    for k in index_info:
        if k not in req + OPTIONAL_BASE_FIELDS + type_specific_opt_fields:
            raise ValueError(f"Unknown key {k} in index info")

    for k in DATE_KEYS:
        try:
            pd.Timestamp(index_info[k])
        except ValueError as e:
            raise ValueError(f"Invalid date format for {k}") from e

    if (tz := index_info.get("timezone")) and tz not in pytz.all_timezones:
        raise ValueError(f"Invalid timezone string: {tz}")

    if not (0 <= index_info["run_hour"] <= 23):
        raise ValueError("run_hour must be between 0 and 23")

    if not (0 <= index_info["run_minute"] <= 59):
        raise ValueError("run_minute must be between 0 and 59")

    swaps_monitor_codes, calendar_identifiers = None, None
    if index_info.get("holiday_calendar"):
        try:
            assert isinstance(hc := index_info["holiday_calendar"], dict)
            if hc.get("mics"):
                calendar_identifiers = [f"MIC:{mic}" for mic in hc["mics"]]
            if hc.get("swaps_monitor_codes"):
                swaps_monitor_codes = hc["swaps_monitor_codes"]
        except (AssertionError, ValidationError):
            raise ValueError("Invalid holiday calendar spec")

    if not swaps_monitor_codes and not calendar_identifiers:
        calendar_identifiers = ["MIC:XNYS"]  # default to nyse
    index_info["_holiday_spec"] = HolidayCalendarSpec(
        calendar_identifiers=calendar_identifiers,
        swaps_monitor_codes=swaps_monitor_codes,
        # TODO: we may have to allow configuration of the weekmask
    )  # type: ignore

    if index_info.get("email_list"):
        if not isinstance(index_info["email_list"], list) or not all(
            isinstance(x, str) for x in index_info["email_list"]
        ):
            raise ValueError("email_list must be a list of strings")

    return index_info


def load_template(
    template_name: str,
    config_file_path: str,
    type_specific_req_fields: list[str],
    type_specific_opt_fields: list[str] = [],
) -> tuple[MerqubeAPIClient, IndexDefinitionPost, dict[str, Any], dict[str, Any]]:
    """
    Loads a template index model to edit and then create a new index from
    """
    index_info = get_index_info(
        config_file_path=config_file_path,
        type_specific_req_fields=type_specific_req_fields,
        type_specific_opt_fields=type_specific_opt_fields,
    )
    token = get_token()

    client = MerqubeAPIClient(token=token)

    template = client.index_post_model_from_existing(template_name)

    assert template.spec and template.spec.index_class_args and template.spec.index_class_args.get("spec")
    inner_spec = template.spec.index_class_args["spec"]

    return client, template, index_info, inner_spec


def _configure_report(template: IndexDefinitionPost, email_list: list[str] | None = None) -> None:
    """
    confifugre index reports
    """
    updated_reports = []
    if not email_list or not template.run_configuration or not template.run_configuration.index_reports:
        logger.warning("Warning, index has no reports to configure or has not been given an email list")
        return

    for ind, report in enumerate(template.run_configuration.index_reports):
        updated_report = cast(IndexReport, deepcopy(report))
        assert updated_report.program_args
        diss_config = json.loads(updated_report.program_args["diss_config"].replace('\\"', '"'))

        if not (dc := diss_config.get("email")) or len(dc) > 1:
            logger.warning(f"Warning, report {ind} has no email config or has more than one config")
            continue

        diss_config["email"][0]["recipients"] = email_list
        updated_report.program_args["diss_config"] = json.dumps(diss_config).replace('"', '\\"')
        updated_reports.append(updated_report)
    template.run_configuration.index_reports = updated_reports


def configure_index(
    template: IndexDefinitionPost, index_info: dict[str, Any], inner_spec: dict[str, Any]
) -> tuple[IndexDefinitionPost, IdentifierUUIDPost | None]:
    """
    set up the index from index info
    """
    for k in TOP_LEVEL:
        setattr(template, k, index_info[k] if k != "base_date" else pd.Timestamp(index_info[k]).strftime("%Y/%m/%d"))

    inner_spec["index_id"] = index_info["name"]
    for k in SPEC_KEYS:
        inner_spec[k] = index_info[k]

    # some indices want "calendar" instead of "holiday_spec"
    inner_spec["holiday_spec"] = inner_spec["calendar"] = index_info["_holiday_spec"]

    name = index_info["name"]
    bbg_ticker = index_info.get("bbg_ticker")
    is_intraday = index_info.get("is_intraday")

    # set the start date at which this will start running
    assert template.run_configuration and template.run_configuration.schedule

    # set runtime
    # make sure to produce the last EOD value immediately on create
    today = freezable_utcnow() - pd.Timedelta(days=5)  # pyright: ignore
    template.run_configuration.schedule.schedule_start = pd.Timestamp(
        year=today.year,
        month=today.month,
        day=today.day,
        hour=index_info["run_hour"],
        minute=index_info["run_minute"],
        second=0,
    ).isoformat()
    template.run_configuration.tzinfo = index_info.get("timezone", "US/Eastern")

    template.stage = Stage.prod
    template.run_configuration.job_enabled = True

    if index_info.get("is_intraday"):
        assert template.intraday and template.intraday.publish_config
        template.intraday.enabled = True

    bbg_identifier_post = None
    if bbg_ticker:
        template.identifiers = [IdentifierUUIDRef(name=bbg_ticker, provider=Provider.bloomberg)]
        if is_intraday:
            assert template.intraday and template.intraday.publish_config and template.intraday.publish_config.__root__
            cast(list[IntradayPublishConfigTarget], template.intraday.publish_config.__root__["price_return"]).append(
                IntradayPublishConfigTarget(
                    __root__=IntradayPublishConfigBloombergTarget(target="bloomberg", active_time_ranges=None)
                )
            )

        bbg_identifier_post = IdentifierUUIDPost(
            name=bbg_ticker, index_name=name, namespace=index_info["namespace"], ticker=bbg_ticker
        )

    _configure_report(template=template, email_list=index_info.get("email_list"))

    return template, bbg_identifier_post


def create_index(
    client: MerqubeAPIClient,
    template: IndexDefinitionPost,
    index_info: dict[str, Any],
    inner_spec: dict[str, Any],
    prod_run: bool,
) -> tuple[IndexDefinitionPost, IdentifierUUIDPost | None]:
    """
    Creates an index from a template
    """
    template, bbg_post = configure_index(template=template, index_info=index_info, inner_spec=inner_spec)

    log_index(template)

    if prod_run:
        # if we are posting to bloomberg, we need to create the identifier first
        if bbg_post:
            res = client.create_identifier(provider=Provider.bloomberg, identifier_post=bbg_post)
            logger.info(f"Created identifier: {res}")

        res = client.create_index(index_def=template)
        logger.info(f"Created index: {res}")

    return template, bbg_post
