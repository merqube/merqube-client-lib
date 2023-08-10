import logging

from merqube_client_lib.logging import get_module_logger
from merqube_client_lib.templates.equity_baskets.schema import (
    ClientDecrementConfig,
    ClientSSTRConfig,
)
from merqube_client_lib.templates.equity_baskets.util import EquityBasketIndexCreator

logger = get_module_logger(__name__, level=logging.DEBUG)


class DecrementIndexCreator(EquityBasketIndexCreator):
    """create a decrement index on top of a SSTR"""

    def __init__(self):
        super().__init__(itype="sstr_decrement", model=ClientDecrementConfig)


class SSTRCreator(EquityBasketIndexCreator):
    """create a SSTR index"""

    def __init__(self):
        super().__init__(itype="sstr", model=ClientSSTRConfig)
