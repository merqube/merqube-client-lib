import abc
import json
import logging
import time
from typing import Any, Type

from merqube_client_lib.api_client import merqube_client as mc
from merqube_client_lib.exceptions import APIError
from merqube_client_lib.logging import get_module_logger
from merqube_client_lib.pydantic_v2_types import (
    ClientIndexConfigBase,
    ClientTemplateResponse,
    IndexDefinitionPost,
    Provider,
    RunStateStatus,
)
from merqube_client_lib.util import get_token, pydantic_to_dict

SPEC_KEYS = ["base_date"]
DATE_KEYS = ["base_date"]
TOP_LEVEL = ["namespace", "name", "title", "base_date", "description"]
TOP_LEVEL_OPTIONAL = ["currency"]

logger = get_module_logger(__name__, level=logging.DEBUG)


def log_index(index: IndexDefinitionPost) -> None:
    """
    Logs the resulting index
    """
    json_formatted_str = json.dumps(json.loads(index.json(exclude_none=True)), indent=4)
    logger.info("Index spec: \n" + json_formatted_str)


class IndexCreator(abc.ABC):
    """
    base class for classes that create ebs
    """

    def __init__(self, *, itype: str, model: Type[ClientIndexConfigBase]) -> None:
        token = get_token()
        self._client = mc.get_client(token=token)
        self._itype = itype
        self._model = model

    def _poll(self, new_id: str, poll: int) -> None:
        """
        polls {poll} minutes until either
        1) it succeeds
        2) it fails
        3) poll minutes have passed
        """
        logger.info(f"Polling for {poll} minutes for the index to finish")
        lrs = self._client.get_last_index_run_state(index_id=new_id)
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
            lrs = self._client.get_last_index_run_state(index_id=new_id)

        raise RuntimeError(
            f"Index failed to create and run successfully in {poll} minutes: {lrs.error or 'unknown error'}. Last status: {lrs.status}"
        )

    def _template_index(self, config: dict[str, Any]) -> ClientTemplateResponse:
        """
        Creates an index manifest and coorepsonding objects from a template
        """
        # pre validate (just to save time) - addl validation may be performed on the server
        self._model.parse_obj(config)

        # the session lib calls raise_for_status already
        try:
            res = self._client.session.post(f"/helper/index-template/{self._itype}", json=config).json()
        except APIError as e:
            raise ValueError(f"Templating error: {e.response_json}") from None
        return ClientTemplateResponse.parse_obj(res)

    def _create(self, config: dict[str, Any], prod_run: bool, poll: int) -> ClientTemplateResponse:
        """
        Creates an index from a template (or just print it if dry run)
        """
        templates = self._template_index(config=config)

        index = templates.post_template
        bbg_post = templates.bbg_ident_template
        initial_target_portfolios = templates.target_ports

        assert index
        log_index(index)

        if initial_target_portfolios:
            logger.info("Initial target portfolios:")
            for itp in initial_target_portfolios:
                formatted = json.dumps(pydantic_to_dict(itp), indent=4, sort_keys=True)
                logger.info(formatted)

        if not prod_run:
            logger.debug("Dry run; exiting without creating the index. Poll, if specified, will be ignored")
            return templates

        # if we are posting to bloomberg, we need to create the identifier first
        if bbg_post:
            res = self._client.create_identifier(provider=Provider.bloomberg, identifier_post=bbg_post)
            logger.info(f"Created identifier: {res}")

        res = self._client.create_index(index_def=index)
        logger.info(f"Created index: {res}")
        new_id = res["id"]

        if initial_target_portfolios:
            self._client.replace_target_portfolio(index_id=new_id, target_portfolio=initial_target_portfolios)

        if poll > 0:
            self._poll(new_id=new_id, poll=poll)

        return templates

    def switch_to_staging(self) -> None:
        """
        points this client at staging
        very helpful for testing server deployments in staging prior to prod
        """
        self._client = mc.get_client(token=get_token(), prefix_url="https://staging.api.merqube.com")

    def create(self, config: dict[str, Any], prod_run: bool, poll: int) -> ClientTemplateResponse:
        """
        can be overridden to inject type specific logic
        """
        return self._create(config=config, prod_run=prod_run, poll=poll)
