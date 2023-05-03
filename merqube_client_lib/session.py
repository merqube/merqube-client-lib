"""
Merqube API Session - subcomponent of the client library wrapper
"""


import json
import os
import uuid
from typing import Any, Optional, Union, cast
from urllib.parse import urljoin

from cachetools import LRUCache, cached
from requests import PreparedRequest, Response, Session
from requests.adapters import HTTPAdapter
from requests.exceptions import HTTPError
from urllib3.util.retry import Retry

from merqube_client_lib.constants import (
    API_URL,
    MERQ_REQUEST_ID_ENV_VAR,
    REQUEST_ID_HEADER,
)
from merqube_client_lib.exceptions import APIError
from merqube_client_lib.logging import get_module_logger
from merqube_client_lib.types import HTTP_METHODS
from merqube_client_lib.types import HTTPMethod as httpm

logger = get_module_logger(__name__)


class TimeoutHTTPAdapter(HTTPAdapter):
    def __init__(self, timeout: int | None = None, **kwargs: Any):
        """
        Adapter to allow for setting timeouts on API calls.
        Timeout should be in seconds
        """
        super().__init__(**kwargs)
        self._timeout = timeout

    def send(self, request: PreparedRequest, **kwargs: Any) -> Response:  # type: ignore  # signature incompatible with supertype
        timeout = kwargs.get("timeout")
        if timeout is None:
            kwargs["timeout"] = self._timeout

        return super().send(request, **kwargs)


class _RetrySession(Session):
    """abstraction over Session that provides retries"""

    def __init__(
        self,
        retries: int = 3,
        backoff_factor: float = 0.3,
        status_forcelist: tuple[int, ...] = (502, 504),  # status codes to retry on
        allowed_methods: list[str] = ["GET"],  # methods to retry on
        request_timeout: int | None = None,
    ):
        super().__init__()
        """
        By default, this session only retries on GET

        DELETE and POST are idempotent, and should be safe to add to the allowed methods list (note though, lost ACKs could change the status code - eg a lost ack on a 200 POST may result in a 409 DUPLICATE being eventually returned, however return codes are not a part of idempotency)

        PUT is sometimes idempotent, but not in some of our APIs; for example we often have a "status" key that must be supplied - two subsequent PUTs will not work
        in our APIs, to "update twice", you must do PUT GET PUT

        see https://developer.mozilla.org/en-US/docs/Glossary/Idempotent
        https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html#urllib3.util.Retry.DEFAULT_ALLOWED_METHODS
        https://restfulapi.net/idempotent-rest-apis/
        """
        for allowed in allowed_methods:
            assert allowed in HTTP_METHODS, f"Should be a valid http method: {', '.join(HTTP_METHODS)}"

        if allowed_methods:
            retry = Retry(
                total=retries,
                read=retries,
                connect=retries,
                backoff_factor=backoff_factor,
                status_forcelist=status_forcelist,
                allowed_methods=allowed_methods,
            )
            adapter = TimeoutHTTPAdapter(timeout=request_timeout, max_retries=retry)
            self.mount("http://", adapter)
            self.mount("https://", adapter)


class _BaseAPISession:
    """Base class for Merqube sessions"""

    def __init__(self, token: Optional[str] = None, **kwargs: Any):
        """
        Create a new merq session using token (the API Key)
        """
        self.session_args = kwargs
        self.token = token

        self._session: Optional[Session] = None
        self._session_pid: int = -1
        self._prefix_url = API_URL
        self.token_type = "APIKEY"

    @property
    def http_session(self) -> Session:
        """
        the http session, i.e. the requests.Session object

        The requests library isn't multiprocessing safe, but claims to be thread safe. So we can just ensure that
        the requests.Session object is only used in the process in which it was created
        """
        pid = os.getpid()
        if pid != self._session_pid or self._session is None:
            if self._session is not None:
                self._session.close()
            self._session = _RetrySession(**self.session_args)
            self._session_pid = pid

        return self._session

    def close(self) -> None:
        if self._session is not None:
            self._session.close()
            self._session = None
            self._session_pid = -1

    def __enter__(self):  # type: ignore
        """
        requests.Session like context manager behavior
        :return: the merq session
        """
        return self

    def __exit__(self, exc_type: str, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def request(
        self,
        method: httpm,
        url: Union[str, bytes],
        params: dict[str, Any] | None = None,
        data: Any = None,
        headers: dict[str, str] | None = None,
        options: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> Response:
        """
        Perform an http request with this session
        request session helpers sess.put, sess.get, etc, call this
        """
        assert params is None or options is None, "both params and options cannot be passed"

        headers = dict(headers) if headers is not None else {}

        # Generate a new requestid if this call isnt being made in a chain that already has it.
        # (eg client calls dataapi, dataapi calls secapi - we dont want the second call to overwrite the original)
        # if this isnt set by a client making a call to one of our APIs, the API itself will generate one (eg customer call)
        # order is: 1) explicitly specified 2) set via chain, 3) generate new
        headers[REQUEST_ID_HEADER] = headers.get(
            REQUEST_ID_HEADER, os.getenv(MERQ_REQUEST_ID_ENV_VAR, str(uuid.uuid4()))
        )

        if self.token:
            headers["Authorization"] = f"{self.token_type} {self.token}"

        url = urljoin(self._prefix_url, cast(str, url))

        options_dict: dict[str, str] = options or {}
        return self.http_session.request(
            method=method.value, url=url, params=options_dict or params, data=data, headers=headers, **kwargs
        )

    def get(self, url: str, **kwargs: Any) -> Response:
        """
        requests.Session like http GET method
        """
        return self.request(httpm.GET, url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> Response:
        """
        requests.Session like http PUT method
        """
        return self.request(httpm.PUT, url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> Response:
        """
        requests.Session like http PATCH method
        """
        return self.request(httpm.PATCH, url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> Response:
        """
        requests.Session like http POST method
        """
        return self.request(httpm.POST, url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> Response:
        """
        requests.Session like http DELETE method
        """
        return self.request(httpm.DELETE, url, **kwargs)


# Public


class MerqubeAPISession(_BaseAPISession):
    """
    API Session tailored to MerQube's API indexapi and its errors
    The session is initialized with an API Key, and that API Key is passed in the Authorization header for all requests
    """

    def __init__(
        self,
        token: str | None = None,
        **kwargs: Any,
    ):
        """can specify your own oauth token,default is no token (only public APIs)"""
        super().__init__(token=token, **kwargs)

    def handle_nonrecoverable(self, res: Response, e: Exception) -> None:
        """helper function that handles a non recoverable error"""
        logger.exception(e)
        try:
            # we may not have a json depending on the response
            rj = res.json()
        except (AttributeError, json.decoder.JSONDecodeError):
            rj = {}
        logger.debug(f"Request failed with status {res.status_code}: {rj}")
        raise APIError(code=res.status_code, response_json=rj)

    def request_raise(self, method: httpm, url: str, **kwargs: Any) -> Response:
        """request method that logs the status code and raises on non 2XX"""
        options = kwargs.get("options")
        options_st = "?" + "&".join([f"{k}={v}" for k, v in options.items()]) if options else ""
        logger.debug(f"Performing {method} on {self._prefix_url}{url}{options_st}")
        res = self.request(method, url, **kwargs)
        try:
            res.raise_for_status()
        except HTTPError as e:
            self.handle_nonrecoverable(res, e)

        return res

    def get(self, url: str, **kwargs: Any) -> Response:
        return self.request_raise(httpm.GET, url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> Response:
        return self.request_raise(httpm.PUT, url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> Response:
        return self.request_raise(httpm.PATCH, url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> Response:
        return self.request_raise(httpm.POST, url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> Response:
        return self.request_raise(httpm.DELETE, url, **kwargs)

    def get_json(self, url: str, options: Optional[dict[str, Any]] = None, **kwargs: Any) -> dict[str, Any]:
        """get where the result is json (as opposed to bytes for csv etc)"""
        return cast(dict[str, Any], self.get(url, options=options, **kwargs).json())

    def get_collection(self, url: str, options: Optional[dict[str, Any]] = None, **kwargs: Any) -> list[Any]:
        """get the inner results array from a collection API"""
        return cast(list[Any], self.get(url, options=options, **kwargs).json()["results"])

    def get_data(self, url: str, options: Optional[dict[str, Any]] = None, **kwargs: Any) -> str:
        """return raw data , most commonly used when options contains format=csv"""
        return self.get(url, options=options, **kwargs).content.decode().strip()

    def get_collection_single(self, url: str, options: Optional[dict[str, Any]] = None, **kwargs: Any) -> Any:
        """
        get the inner results array from a collection API when there is only one expected result
        for example, sess.get("index?name=XXX")
        """
        res = self.get_collection(url, options=options, **kwargs)
        num_results = len(res)
        if num_results != 1:
            raise APIError(400, {"message": f"Only one result was expected but {num_results} found!"})
        return res[0]


@cached(cache=LRUCache(maxsize=256))
def get_merqube_session(token: str | None = None, **session_args: Any) -> MerqubeAPISession:
    """
    Cached; returns a session with the given token
    """
    return MerqubeAPISession(token=token, **session_args)


@cached(cache=LRUCache(maxsize=1))
def get_public_merqube_session() -> MerqubeAPISession:
    """
    Returns a (no token) session.
    This can be used to access all data in the `default` namespace (world viewable)
    """
    return MerqubeAPISession()
