"""
simple tests for logger
"""
import datetime
import logging
import os
import tempfile
import time

from freezegun import freeze_time

from merqube_client_lib.constants import (
    MERQ_REQUEST_ID_ENV_VAR,
    MERQ_REQUEST_REMOTE_ADDR_ENV_VAR,
    MERQ_RUN_ID_ENV_VAR,
)
from merqube_client_lib.logging import get_module_logger


def set_request_vars(remote_addr, req_id):
    # api_infra package does this - but we dont want a cyclic dependency
    os.environ[MERQ_REQUEST_REMOTE_ADDR_ENV_VAR] = remote_addr
    os.environ[MERQ_REQUEST_ID_ENV_VAR] = req_id


def test_instantiate_logger_file():
    """test root logger instantiation"""
    with tempfile.TemporaryDirectory() as tdir:
        pid = os.getpid()
        f = os.path.join(tdir, "mylogfile.txt")
        # When you pass a timezone unaware datetime or a string to freeze_time, it assumes that this is in UTC and stores it without adjustment.
        # When you pass in a timezone aware datetime, freeze_time will convert it to UTC first before storing it.
        # If you call time.localtime, it will take the stored UTC datetime and return it in local time based on the machine's timezone (time.timezone).
        # So if you want to set what time.localtime will return you need to pass in a timezone aware datetime set to the machine's timezone.
        # In this test case the log Formatter uses time.localtime to show the log timestamp.
        local_timezone = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
        local_time = time.localtime()
        is_dst = local_time.tm_isdst == 1
        if is_dst:
            month = 6
        else:
            month = 12
        with freeze_time(datetime.datetime(2021, month, 14, 6, 1, 6, tzinfo=local_timezone)):
            logger = get_module_logger("merqutil_tests", filename=f, level=logging.DEBUG)
            logger.debug("Logger testing")
            assert (
                open(f, "r").read()
                == f"[2021-{month:02d}-14 06:01:06,000] [merqutil_tests] [DEBUG] [{pid}] Logger testing\n"
            )

            set_request_vars("6.6.6.6", "dc665804612940959928c9acbec4ffe9")
            logger.debug("Testing api")
            set_request_vars("8.6.6.6", "aaaa5804612940959928c9acbec4ffe9")
            logger.debug("Testing api again")
            os.environ[MERQ_RUN_ID_ENV_VAR] = "11112222333344445555666677778888"
            logger.debug("Testing with both vars")
            del os.environ[MERQ_REQUEST_ID_ENV_VAR]
            del os.environ[MERQ_REQUEST_REMOTE_ADDR_ENV_VAR]
            logger.debug("Testing with just run var")
            del os.environ[MERQ_RUN_ID_ENV_VAR]
            logger.debug("Testing without")

            assert (
                open(f, "r").read().strip()
                == f"""[2021-{month:02d}-14 06:01:06,000] [merqutil_tests] [DEBUG] [{pid}] Logger testing
[2021-{month:02d}-14 06:01:06,000] [req-id:dc665804612940959928c9acbec4ffe9] [ip:6.6.6.6] [merqutil_tests] [DEBUG] [{pid}] Testing api
[2021-{month:02d}-14 06:01:06,000] [req-id:aaaa5804612940959928c9acbec4ffe9] [ip:8.6.6.6] [merqutil_tests] [DEBUG] [{pid}] Testing api again
[2021-{month:02d}-14 06:01:06,000] [req-id:aaaa5804612940959928c9acbec4ffe9] [run-id:11112222333344445555666677778888] [ip:8.6.6.6] [merqutil_tests] [DEBUG] [{pid}] Testing with both vars
[2021-{month:02d}-14 06:01:06,000] [run-id:11112222333344445555666677778888] [merqutil_tests] [DEBUG] [{pid}] Testing with just run var
[2021-{month:02d}-14 06:01:06,000] [merqutil_tests] [DEBUG] [{pid}] Testing without"""
            )
