"""
Integration tests for the API client class
"""
from merqube_client_lib.secapi.client import get_client


def test_mapping_table():
    """
    Test the mapping table for the security definitions
    """
    public = get_client()
    all_public_indices = public.get_security_definitions_mapping_table(sec_type="index")

    for k, v in {
        "NWSALTVI": "2963d69a-2c81-4ee5-9c0e-98fc1e476f2a",
        "UBCIPACC": "b47bc829-82b4-4610-921f-9dc73936a10b",
        "MQUSTRAV": "27514b7a-3575-4da1-a1f1-c22d0e361c78",
    }.items():
        assert all_public_indices[k] == v


def test_mapping_table_for_specific_names():
    public = get_client()
    mt = public.get_security_definitions_mapping_table(sec_type="index", sec_names=["NWSALTVI", "UBCIPACC"])
    assert mt["NWSALTVI"] == "2963d69a-2c81-4ee5-9c0e-98fc1e476f2a"
    assert mt["UBCIPACC"] == "b47bc829-82b4-4610-921f-9dc73936a10b"


def test_mapping_table_for_specific_ids():
    public = get_client()
    mt = public.get_security_definitions_mapping_table(
        sec_type="index", sec_ids=["2963d69a-2c81-4ee5-9c0e-98fc1e476f2a", "b47bc829-82b4-4610-921f-9dc73936a10b"]
    )
    assert mt["2963d69a-2c81-4ee5-9c0e-98fc1e476f2a"] == "NWSALTVI"
    assert mt["b47bc829-82b4-4610-921f-9dc73936a10b"] == "UBCIPACC"
