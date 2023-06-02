import datetime

from merqube_client_lib.api_client.merqube_client import MerqubeAPIClientSingleIndex
from merqube_client_lib.pydantic_types import Administrative, Role, Status
from tests.unit.fixtures.test_manifest import manifest


def test_single():
    """
    There is also a real integration test of this that tests more methods.
    """

    class fake_session:
        call_count = 0

        def get_collection_single(self, *args, **kwargs):
            if self.call_count == 0:
                self.call_count += 1
                return {"id": "valid1id"}
            return manifest

    client = MerqubeAPIClientSingleIndex(index_name="valid1", user_session=fake_session())

    assert client.get_manifest() == manifest

    # show some pydantic models:
    model = client.get_model()
    assert model.status == Status(
        created_at="2022-06-07T23:15:31.212502",
        created_by="test@merqube.com",
        last_modified="2023-01-25T22:40:25.552308",
        last_modified_by="test@merqube.com",
        locked_after=datetime.datetime(2023, 1, 25, 22, 41),
    )
    assert model.administrative == Administrative(role=Role.administration)
