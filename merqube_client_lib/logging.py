"""
Module that handles logging
"""
import logging
import logging.handlers
import os

from merqube_client_lib.constants import (
    MERQ_REQUEST_ID_ENV_VAR,
    MERQ_REQUEST_REMOTE_ADDR_ENV_VAR,
    MERQ_RUN_ID_ENV_VAR,
)


def _get_file_handler(filename: str) -> logging.Handler:
    # 100MB log, up to 5 (enhancement: take these as params)
    handler = logging.handlers.RotatingFileHandler(filename, maxBytes=100000000, backupCount=5)
    handler.setFormatter(FORMATTER)

    return handler


class MerqFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_str = super().format(record)
        req_id = os.getenv(MERQ_REQUEST_ID_ENV_VAR)
        run_id = os.getenv(MERQ_RUN_ID_ENV_VAR)
        remote_addr = os.getenv(MERQ_REQUEST_REMOTE_ADDR_ENV_VAR)
        if req_id is None and run_id is None and remote_addr is None:
            return log_str

        splice = ""
        if req_id is not None:
            splice += f" [req-id:{req_id}]"
        if run_id is not None:
            splice += f" [run-id:{run_id}]"
        if remote_addr is not None:
            splice += f" [ip:{remote_addr}]"

        # Move the request id after time
        time_offset = 25
        return log_str[0:time_offset] + splice + log_str[time_offset:]


FORMATTER = MerqFormatter("[%(asctime)s] [%(name)s] [%(levelname)s] [%(process)d] %(message)s")


def get_module_logger(
    mod_name: str, level: int = logging.DEBUG, filename: str | None = None, propagate: bool = False
) -> logging.Logger:
    """
    Call this from each module with __name__
    see https://docs.python.org/3/howto/logging.html#advanced-logging-tutorial
    """
    logger = logging.getLogger(mod_name)
    logger.setLevel(level)

    if not propagate:
        logger.propagate = False

    handler = logging.StreamHandler()
    handler.setFormatter(FORMATTER)
    logger.addHandler(handler)

    if filename:
        fhandler = _get_file_handler(filename)
        logger.addHandler(fhandler)

    return logger
