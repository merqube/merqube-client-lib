import os
from unittest.mock import ANY, MagicMock, call

import pytest
import requests

from merqube_client_lib import session
from merqube_client_lib.api_client import base
from merqube_client_lib.exceptions import PERMISSION_ERROR_RES, APIError
from merqube_client_lib.session import MerqubeAPISession, _BaseAPISession, _RetrySession
from merqube_client_lib.types import HTTP_METHODS
from tests.unit.helpers import MockRequestsResponse


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
@pytest.mark.parametrize("prefix", ["", "apiclient"])
@pytest.mark.parametrize(
    "headers", [{"header1": "value2"}, {"header2": "value2", "foo": "bar"}, {"foo": "bar", "X-Request-ID": "testid"}]
)
def test_session_methods(session_class, method, prefix, headers, monkeypatch):
    class FakeUUID:
        hex = "testid"

    monkeypatch.setattr("uuid.uuid4", lambda: FakeUUID())
    mock_retry = MagicMock()
    monkeypatch.setattr("merqube_client_lib.session._RetrySession", mock_retry)

    token = "a token"

    kwargs = {"token": token}
    if session_class is MerqubeAPISession and prefix:
        kwargs["req_id_prefix"] = prefix
    sess = session_class(**kwargs)

    url = "/test"
    getattr(sess, method)(url=url, headers=headers, options={"a": "b", "c": "d"}, some_kwarg="foo")
    exp_headers = {"Authorization": f"APIKEY {token}"}
    if session_class is MerqubeAPISession:
        if "X-Request-ID" in headers:
            exp_headers["X-Request-ID"] = headers["X-Request-ID"]
        elif prefix:
            exp_headers["X-Request-ID"] = prefix + "_testid"
        else:
            exp_headers["X-Request-ID"] = "mqu_py_client_testid"
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

    assert len(caplog.records) == expected_retries
    for i in range(0, expected_retries):
        expected = expected_retries - i - 1
        assert (
            f"Retrying (Retry(total={expected}, connect={expected}, read={expected_retries}, redirect=None, status=None))"
            in caplog.records[i].message
        )


@pytest.mark.parametrize("direct_req_id", [None, "my-own-req-id"])
@pytest.mark.parametrize("prefix", [None, "testprefix"])
def test_merq_session_req_ids(direct_req_id, prefix, monkeypatch):
    class FakeUUID:
        hex = "testid"

    monkeypatch.setattr("uuid.uuid4", lambda: FakeUUID())

    kwargs = {"token": "token"}
    if prefix:
        kwargs["req_id_prefix"] = prefix

    session = MerqubeAPISession(**kwargs)

    low_lvl_request = MagicMock()
    session.request = low_lvl_request

    session.get_collection("/index", headers={"X-Request-ID": direct_req_id})

    if direct_req_id:
        assert low_lvl_request.call_args_list[0].kwargs["headers"]["X-Request-ID"] == direct_req_id
    elif prefix:
        assert low_lvl_request.call_args_list[0].kwargs["headers"]["X-Request-ID"] == "testprefix_testid"
    else:
        assert low_lvl_request.call_args_list[0].kwargs["headers"]["X-Request-ID"] == "mqu_py_client_testid"


@pytest.mark.parametrize(
    "options, expected", [(None, {}), ({"foo": "bar"}, {"foo": "bar"}), ({"names": ["n1", "n2"]}, {"names": "n1,n2"})]
)
def test_options(options, expected):
    ch = MagicMock(return_value=[{"foo1": "bar1"}, {"foo2": "bar2"}])

    class mock_session:
        def __init__(self):
            self.get_collection = ch

    cl = base._MerqubeApiClientBase(user_session=mock_session())

    assert cl._collection_helper(url="test_url", query_options=options) == [{"foo1": "bar1"}, {"foo2": "bar2"}]
    assert ch.call_args_list == [call(url="test_url", options=expected, raise_perm_errors=False)]


@pytest.mark.parametrize("raise_perm_errors, has_error", [(True, True), (True, False), (False, True), (False, False)])
def test_collection_perm_errors(raise_perm_errors, has_error):
    """Test that the collection helper raises PermissionError when raise_perm_errors is True and the response has the error code"""
    sess = MerqubeAPISession()

    mock_res_j = {"results": [{"foo": "bar"}]}
    if has_error:
        mock_res_j["error_codes"] = [PERMISSION_ERROR_RES]

    sess.get = MagicMock(return_value=MockRequestsResponse(status_code=200, json=mock_res_j))

    if raise_perm_errors and has_error:
        with pytest.raises(PermissionError):
            sess.get_collection("/index", raise_perm_errors=raise_perm_errors)
    else:
        sess.get_collection("/index", raise_perm_errors=raise_perm_errors)
