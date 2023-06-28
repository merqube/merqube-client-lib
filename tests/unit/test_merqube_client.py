from unittest.mock import MagicMock

import pytest

from merqube_client_lib.api_client.merqube_client import MerqubeAPIClientSingleIndex
from merqube_client_lib.pydantic_types import (
    Administrative,
    IdentifierUUIDPost,
    Provider,
    Role,
    Status,
)
from tests.unit.fixtures.test_manifest import manifest


def test_single():
    """
    There is also a real integration test of this that tests more methods.
    """

    class fake_session:
        def get_collection_single(self, *args, **kwargs):
            return manifest

        def get_json(self, *args, **kwargs):
            return manifest

    client = MerqubeAPIClientSingleIndex(index_name="valid1", user_session=fake_session())

    assert client.get_manifest() == manifest

    # show some pydantic models:
    model = client.model
    assert model.status == Status(
        created_at="2022-06-07T23:15:31.212502",
        created_by="test@merqube.com",
        last_modified="2023-01-25T22:40:25.552308",
        last_modified_by="test@merqube.com",
    )
    assert model.administrative == Administrative(role=Role.administration)


@pytest.mark.parametrize(
    "existing, should_post, should_work",
    [
        ([], True, True),
        ([{"index_name": "the_same", "name": "xxx", "namespace": "test", "ticker": "xxx"}], False, True),
        ([{"index_name": "different", "name": "xxx", "namespace": "test", "ticker": "xxx"}], False, False),
    ],
    ids=["not_found_ok", "same_ok", "different_fail"],
)
def test_identifier_collision(existing, should_post, should_work):
    """
    There is also a real integration test of this that tests more methods.
    """

    fake_post = MagicMock()

    class fake_session:
        def __init__(self, *args, **kwargs):
            self.post = fake_post
            self.get_collection_single = MagicMock(return_value=manifest)

        def get_collection(self, *args, **kwargs):
            return existing

    client = MerqubeAPIClientSingleIndex(index_name="valid1", user_session=fake_session())

    # not found prior, do the post
    if should_work:
        client.create_identifier(
            Provider.bloomberg,
            IdentifierUUIDPost(index_name="the_same", name="foo", ticker="bar"),
        )
    else:
        with pytest.raises(ValueError):
            client.create_identifier(
                Provider.bloomberg,
                IdentifierUUIDPost(index_name="the_same", name="foo", ticker="bar"),
            )

    if should_post:
        assert len(fake_post.call_args_list) == 1
