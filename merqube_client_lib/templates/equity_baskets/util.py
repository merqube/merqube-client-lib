import abc
import json
import logging
import time
from typing import Any, cast

import pandas as pd

from merqube_client_lib.api_client import merqube_client as mc
from merqube_client_lib.logging import get_module_logger
from merqube_client_lib.pydantic_types import (
    ClientIndexConfigBase,
    IdentifierUUIDPost,
    IndexDefinitionPost,
    Provider,
    RunStateStatus,
)
from merqube_client_lib.types import CreateReturn
from merqube_client_lib.util import get_token, pydantic_to_dict

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


def get_inner_spec(template: IndexDefinitionPost) -> dict[str, Any]:
    """
    Gets the inner spec of the index. Defined externally since it is used in some binary scripts
    """
    assert template.spec and template.spec.index_class_args and template.spec.index_class_args.get("spec")
    return cast(dict[str, Any], template.spec.index_class_args["spec"])


class EquityBasketIndexCreator(abc.ABC):
    """
    base class for classes that create ebs
    """

    def __init__(self, itype: str, model: ClientIndexConfigBase) -> None:
        token = get_token()
        self._client = mc.get_client(token=token)

        assert itype in ["sstr", "sstr_decrement", "multi_eb"]
        self._itype = itype

        self._model = model

    def _poll(self, client: mc.MerqubeAPIClient, new_id: str, poll: int) -> None:
        """
        polls {poll} minutes until either
        1) it succeeds
        2) it fails
        3) poll minutes have passed
        """
        logger.info(f"Polling for {poll} minutes for the index to finish")
        lrs = client.get_last_index_run_state(index_id=new_id)
        for _ in range(poll):
            match lrs.status:
                case RunStateStatus.PENDING_CREATION:
                    logger.info("Index is still pending creation, please wait...")
                case RunStateStatus.RUNNING:
                    logger.info("Index is running, please wait...")
                case RunStateStatus.FAILED:
                    break
                case RunStateStatus.SUCCEEDED:
                    logger.info("Index created and ran successfully!")
                    return
            time.sleep(60)
            lrs = client.get_last_index_run_state(index_id=new_id)

        raise RuntimeError(
            f"Index failed to create and run successfully in {poll} minutes: {lrs.error or 'unknown error'}. Last status: {lrs.status}"
        )

    def _template_index(
        self,
        config: dict[str, Any],
    ) -> tuple[IndexDefinitionPost, IdentifierUUIDPost | None]:
        """
        Creates an index manifest and coorepsonding objects from a template
        """
        # pre validate (just to save time) - addl validation may be performed on the server
        self._model.parse_obj(config)

        return self._client.post(f"/helper/index-template/{self._itype}", json=config)

    def _create_index(res, prod_run: bool, poll: int = 0):
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

        if poll == 0:
            return template, bbg_post

        self._poll(client=client, new_id=new_id, poll=poll)
        return template, bbg_post

    def create(self, config: dict[str, Any], prod_run: bool, poll: int) -> CreateReturn:
        templates = self._template_index(config=config, prod_run=prod_run, poll=poll)

        template = "a"
        bbg_post = "a"
        initial_target_portfolio = "a"

        log_index(template)

        if initial_target_portfolios:
            logger.info("Initial target portfolios:")
            for date, itp in initial_target_portfolios:
                formatted = json.dumps(pydantic_to_dict(itp), indent=4, sort_keys=True)
                logger.info(f"{date}: {formatted}")

        if not prod_run:
            logger.debug("Dry run; exiting without creating the index. Poll, if specified, will be ignored")
            return template, bbg_post

        self._create_index())
