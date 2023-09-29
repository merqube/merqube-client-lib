"""
Options based index creators
"""
import logging

from merqube_client_lib.logging import get_module_logger
from merqube_client_lib.templates.configs import ClientBufferSimpleConfig
from merqube_client_lib.templates.util import IndexCreator

logger = get_module_logger(__name__, level=logging.DEBUG)


class SimpleBufferCreator(IndexCreator):
    """create a defined outcome index"""

    def __init__(self) -> None:
        super().__init__(itype="buffer_simple", model=ClientBufferSimpleConfig)
