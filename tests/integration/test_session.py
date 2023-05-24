import os

import pytest
import requests

from merqube_client_lib.constants import MERQ_REQUEST_ID_ENV_VAR
from merqube_client_lib.exceptions import APIError
from merqube_client_lib.session import MerqubeAPISession, _BaseAPISession


@pytest.mark.parametrize("timeout_key", ["request_timeout", "timeout"], ids=["globally", "on-request"])
@pytest.mark.parametrize(
    "timeout, delay, should_raise",
    [(None, 4, False), (2, 1, False), (3, 5, True)],
    ids=[
        "no-timeout",
        "custom-timeout-lower-delay",
        "custom-timeout-greater-delay",
    ],
)
def test_timeout(caplog, timeout_key, timeout, delay, should_raise):
    kwargs = {timeout_key: timeout} if timeout is not None else {}
    session_kwargs = {}
    request_kwargs = {}
    if timeout_key == "request_timeout":
        session_kwargs = kwargs
    else:
        request_kwargs = kwargs

    # Postman Echo is a service they provide to tests REST clients, providing utility endpoints
    # like `/delay/{seconds}` in order to check this kind of cases
    sess = _BaseAPISession(retries=1, **session_kwargs)
    sess._prefix_url = "https://postman-echo.com"
    url = f"/delay/{delay}"
    if should_raise:
        with pytest.raises(requests.exceptions.ConnectionError):
            sess.get(url, **request_kwargs)
        assert "ReadTimeoutError" in caplog.text
    else:
        response = sess.get(url)
        assert response.status_code == 200


def test_request_id_generated():
    sess = MerqubeAPISession()
    with pytest.raises(APIError) as e:
        sess.get("/api/v1/invalid-endpoint")
    assert e.value.request_id is not None


def test_request_id_user_passed():
    sess = MerqubeAPISession()
    try:
        os.environ[MERQ_REQUEST_ID_ENV_VAR] = "ABCD-1234"
        with pytest.raises(APIError) as e:
            sess.get("/api/v1/invalid-endpoint")
        assert e.value.request_id == "ABCD-1234"
    finally:
        del os.environ[MERQ_REQUEST_ID_ENV_VAR]
