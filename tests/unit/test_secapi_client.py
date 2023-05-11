"""
Tests for the secapi client
"""
from merqube_client_lib.secapi.client import get_client


def test_public_client():
    """test instantiating without credentials"""
    # twice to trigger cache
    public = get_client()
    public2 = get_client()
    assert public is public2
