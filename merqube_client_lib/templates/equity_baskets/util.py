import json
import logging
from copy import deepcopy
from typing import Any, Type, cast

import pandas as pd
from pydantic import BaseModel

from merqube_client_lib.api_client.merqube_client import MerqubeAPIClient
from merqube_client_lib.logging import get_module_logger
from merqube_client_lib.pydantic_types import (
    HolidayCalendarSpec,
    IdentifierUUIDPost,
    IdentifierUUIDRef,
    IndexDefinitionPost,
    IndexReport,
    IntradayPublishConfigBloombergTarget,
    IntradayPublishConfigTarget,
    Provider,
    Stage,
)
from merqube_client_lib.templates.equity_baskets.schema import ClientIndexConfigBase
from merqube_client_lib.types import TargetPortfoliosDates
from merqube_client_lib.util import freezable_utcnow_ts, get_token, pydantic_to_dict

SPEC_KEYS = ["base_date"]
DATE_KEYS = ["base_date"]
TOP_LEVEL = ["namespace", "name", "title", "base_date", "description"]
TOP_LEVEL_OPTIONAL = ["currency"]

logger = get_module_logger(__name__, level=logging.DEBUG)


def read_file(filename: str) -> list[Any]:
    """reads portfolio/overrides files"""
    return list(pd.read_csv(filename, float_precision="round_trip").to_dict(orient="index").values())


def log_index(index: IndexDefinitionPost) -> None:
    """
    Logs the resulting index
    """
    json_formatted_str = json.dumps(json.loads(index.json(exclude_none=True)), indent=4)
    logger.info("Index spec: \n" + json_formatted_str)


def get_index_info(config: dict[str, Any], model: Type[ClientIndexConfigBase]) -> ClientIndexConfigBase:
    """
    load index specific info from config file + validate the data
    """
    # validate:

    index_info = model.parse_obj(config)

    kwargs = {}
    if hc := getattr(index_info, "holiday_calendar", None):
        if hc.mics:
            kwargs["calendar_identifiers"] = [f"MIC:{mic}" for mic in hc.mics]
        if hc.swaps_monitor_codes:
            kwargs["swaps_monitor_codes"] = hc.swaps_monitor_codes

    if kwargs == {}:
        logger.warning("Warning, no calendar identifiers or swaps monitor codes found, defaulting to nyse")
        kwargs["calendar_identifiers"] = ["MIC:XNYS"]

    # TODO: we may have to allow configuration of the weekmask
    index_info.holiday_spec = HolidayCalendarSpec(**kwargs)  # type: ignore

    return index_info


def get_inner_spec(template: IndexDefinitionPost) -> dict[str, Any]:
    """
    Gets the inner spec of the index
    """
    assert template.spec and template.spec.index_class_args and template.spec.index_class_args.get("spec")
    return cast(dict[str, Any], template.spec.index_class_args["spec"])


def load_template(
    template_name: str,
    config: dict[str, Any],
    model: Type[ClientIndexConfigBase],
) -> tuple[MerqubeAPIClient, IndexDefinitionPost, BaseModel, dict[str, Any]]:
    """
    Loads a template index model to edit and then create a new index from
    """
    index_info = get_index_info(config=config, model=model)
    token = get_token()

    client = MerqubeAPIClient(token=token)

    template = client.index_post_model_from_existing(index_name=template_name)

    return client, template, index_info, get_inner_spec(template)


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
    template: IndexDefinitionPost, index_info: ClientIndexConfigBase, inner_spec: dict[str, Any]
) -> tuple[IndexDefinitionPost, IdentifierUUIDPost | None]:
    """
    set up the index from index info
    """
    for k in TOP_LEVEL:
        v = getattr(index_info, k)
        if k == "base_date":
            v = pd.Timestamp(v).strftime("%Y/%m/%d")
        setattr(template, k, v)

    for k in TOP_LEVEL_OPTIONAL:
        if v := getattr(index_info, k, None):
            setattr(template, k, v)

    inner_spec["index_id"] = index_info.name
    for k in SPEC_KEYS:
        inner_spec[k] = getattr(index_info, k)

    if index_info.base_value is not None:
        inner_spec["base_val"] = index_info.base_value

    # some indices want "calendar" instead of "holiday_spec"
    inner_spec["holiday_spec"] = inner_spec["calendar"] = index_info.holiday_spec

    name = index_info.name
    bbg_ticker = index_info.bbg_ticker
    is_intraday = index_info.is_intraday

    # set the start date at which this will start running
    assert template.run_configuration and template.run_configuration.schedule

    # set runtime
    # make sure to produce the last EOD value immediately on create
    today = freezable_utcnow_ts() - pd.Timedelta(days=5)  # pyright: ignore
    template.run_configuration.schedule.schedule_start = pd.Timestamp(
        year=today.year,
        month=today.month,
        day=today.day,
        hour=index_info.run_hour,
        minute=index_info.run_minute,
        second=0,
    ).isoformat()
    template.run_configuration.tzinfo = index_info.timezone

    template.stage = Stage.prod
    template.run_configuration.job_enabled = True

    if index_info.is_intraday:
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
            name=bbg_ticker, index_name=name, namespace=index_info.namespace, ticker=bbg_ticker
        )

    _configure_report(template=template, email_list=index_info.email_list)

    return template, bbg_identifier_post


def create_index(
    client: MerqubeAPIClient,
    template: IndexDefinitionPost,
    index_info: ClientIndexConfigBase,
    inner_spec: dict[str, Any],
    prod_run: bool,
    initial_target_portfolios: TargetPortfoliosDates | None = None,
) -> tuple[IndexDefinitionPost, IdentifierUUIDPost | None]:
    """
    Creates an index from a template
    """
    template, bbg_post = configure_index(template=template, index_info=index_info, inner_spec=inner_spec)

    log_index(template)

    if initial_target_portfolios:
        logger.info("Initial target portfolios:")
        for date, itp in initial_target_portfolios:
            formatted = json.dumps(pydantic_to_dict(itp), indent=4, sort_keys=True)
            logger.info(f"{date}: {formatted}")

    if not prod_run:
        logger.debug("Dry run; exiting without creating the index")
        return template, bbg_post

    # if we are posting to bloomberg, we need to create the identifier first
    if bbg_post:
        res = client.create_identifier(provider=Provider.bloomberg, identifier_post=bbg_post)
        logger.info(f"Created identifier: {res}")

    res = client.create_index(index_def=template)
    logger.info(f"Created index: {res}")
    new_id = res["id"]

    for date, itp in initial_target_portfolios or []:
        logger.info(f"Pushing target portfolio for {date}")
        client.replace_target_portfolio(index_id=new_id, target_portfolio=pydantic_to_dict(itp))

    return template, bbg_post
