from merqube_client_lib.pydantic_v2_types import ClientTemplateResponse
from merqube_client_lib.templates.equity_baskets.creators import (
    MultiEBIndexCreator,
    SSTRIndexCreator,
)
from tests.unit.templates.test_create_index import EB, SS


def test_template_ss_index():
    conf = SS()
    cl = SSTRIndexCreator()
    res = cl.create(config=conf, poll=0, prod_run=False)

    # dont assert the actual manifest because server may change details in the manifest
    assert isinstance(res, ClientTemplateResponse)


def test_multi_eb():
    conf = EB()
    cl = MultiEBIndexCreator()
    res = cl.create(config=conf, poll=0, prod_run=False)

    # dont assert the actual manifest because server may change details in the manifest
    assert isinstance(res, ClientTemplateResponse)
