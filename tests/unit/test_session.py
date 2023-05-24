import os
from unittest.mock import ANY, MagicMock, call

import pytest
import requests

from merqube_client_lib import session
from merqube_client_lib.exceptions import APIError
from merqube_client_lib.session import MerqubeAPISession, _BaseAPISession, _RetrySession
from merqube_client_lib.types import HTTP_METHODS


class MockRequestsResponse(object):
    def __init__(self, status_code, json):
        self.status_code = status_code
        self._json = json

    def json(self):
        return self._json


def test_handle_nonrecoverable():
    exc = Exception("test")

    sess = session.get_merqube_session()
    with pytest.raises(APIError) as e:
        sess.handle_nonrecoverable(MockRequestsResponse(500, {"error": "test"}), exc, req_id="testid")

    assert e.value.code == 500
    assert e.value.response_json == {"error": "test"}
    assert e.value.request_id == "testid"


@pytest.mark.parametrize(
    "allowed_methods, expected",
    [
        (["UNSUPPORTED", "DELETE", "POST"], f"Should be a valid http method: {', '.join(HTTP_METHODS)}"),
    ],
)
def test_retry_sesion_allowed_methods_failed(allowed_methods, expected):
    with pytest.raises(AssertionError) as excinfo:
        _RetrySession(allowed_methods=allowed_methods)
    assert excinfo.value.args[0] == expected


@pytest.mark.parametrize(
    "session_class, arguments",
    [
        (_RetrySession, ()),
        (_BaseAPISession, {"token": "token"}),
        (MerqubeAPISession, {"token": "token"}),
    ],
)
@pytest.mark.parametrize(
    "allowed_methods, called, expected_allowed_methods",
    [
        ([], False, []),
        (["GET", "DELETE", "POST"], True, ["GET", "DELETE", "POST"]),
        (["GET", "DELETE"], True, ["GET", "DELETE"]),
    ],
)
def test_retry_session_allowed_methods_successfully(
    session_class, arguments, allowed_methods, called, expected_allowed_methods, monkeypatch
):
    mock_retry = MagicMock()
    monkeypatch.setattr("merqube_client_lib.session.Retry", mock_retry)
    sess = session_class(*arguments, allowed_methods=allowed_methods)
    if isinstance(sess, _BaseAPISession):
        assert sess.http_session is not None

    assert mock_retry.called is called
    if called:
        assert len(mock_retry.call_args_list) == 1
        assert sorted(mock_retry.call_args_list[0].kwargs["allowed_methods"]) == sorted(expected_allowed_methods)
        assert mock_retry.call_args_list == [
            call(
                total=3,
                read=3,
                connect=3,
                backoff_factor=0.3,
                status_forcelist=(502, 504),
                allowed_methods=ANY,
            )
        ]


def test_process_change():
    sess = _BaseAPISession()
    http_sess = sess.http_session
    assert http_sess == sess.http_session
    assert sess._session_pid == os.getpid()

    sess._session_pid += 1  # fake a process change
    assert http_sess is not sess.http_session
    assert sess._session_pid == os.getpid()
    sess.close()
    assert sess._session is None
    assert sess._session_pid == -1


def test_contextual():
    with _BaseAPISession() as sess:
        assert sess.http_session is not None
        assert sess._session_pid == os.getpid()
    assert sess._session is None
    assert sess._session_pid == -1


SESSION_METHODS = [
    "get",
    "put",
    "post",
    "patch",
    "delete",
]
SESSION_CLASSES = [
    _BaseAPISession,
    MerqubeAPISession,
]


@pytest.mark.parametrize("session_class", SESSION_CLASSES)
@pytest.mark.parametrize("method", SESSION_METHODS)
@pytest.mark.parametrize("headers", [{"header1": "value2"}, {"header2": "value2", "foo": "bar"}])
def test_session_methods(session_class, method, headers, monkeypatch):
    monkeypatch.setattr("uuid.uuid4", lambda: "testid")
    mock_retry = MagicMock()
    monkeypatch.setattr("merqube_client_lib.session._RetrySession", mock_retry)

    token = "a token"
    sess = session_class(token=token)

    url = "/test"
    getattr(sess, method)(url=url, headers=headers, options={"a": "b", "c": "d"}, some_kwarg="foo")
    exp_headers = {"Authorization": f"APIKEY {token}"}
    if session_class is MerqubeAPISession:
        exp_headers["X-Request-ID"] = "testid"
    if headers:
        exp_headers.update(headers)

    assert sess.http_session.method_calls[-1] == call.request(
        method=method.upper(),
        url="https://api.merqube.com/test",
        params={"a": "b", "c": "d"},
        data=None,
        headers=exp_headers,
        some_kwarg="foo",
    ), str(headers)


@pytest.mark.parametrize("retries, expected_retries", [(None, 3), (2, 2)])
def test_retries_and_fail(caplog, retries, expected_retries):
    session_kwargs = {"retries": retries} if retries is not None else {}
    sess = _BaseAPISession(**session_kwargs)
    sess._prefix_url = "http://non-existent.merqube.com"
    with pytest.raises(requests.exceptions.ConnectionError):
        sess.get("/foo")

    assert len(caplog.records) == expected_retries + 1
    for i in range(0, expected_retries):
        expected = expected_retries - i - 1
        assert (
            f"Retrying (Retry(total={expected}, connect={expected}, read={expected_retries}, redirect=None, status=None))"
            in caplog.records[i + 1].message
        )
