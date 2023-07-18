"""
Merqube API Session - subcomponent of the client library wrapper
"""

import json
import os
import uuid
from copy import deepcopy
from typing import Any, Optional, cast
from urllib.parse import urljoin

from cachetools import LRUCache, cached
from requests import PreparedRequest, Response, Session
from requests.adapters import HTTPAdapter
from requests.exceptions import HTTPError
from urllib3.util.retry import Retry

from merqube_client_lib.constants import (
    API_URL,
    MERQ_CLIENT_PREFIX,
    MERQ_REQUEST_ID_ENV_VAR,
    REQUEST_ID_HEADER,
)
from merqube_client_lib.exceptions import PERMISSION_ERROR_RES, APIError
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
        By default, this session only retries on GET, but you may enable for DELETE, POST, and PUT as well. 
        Note that when considering idempotency, only the server state is considered, not the client state.
        See https://developer.mozilla.org/en-US/docs/Glossary/Idempotent

        In our APIs, DELETE, POST, and PUT are all idempotent with respect to the server state.

        However, from the client side, e.g., a lost ACK on a POST may result in a 409 DUPLICATE being returned.
        Similarly, a lost ACK on DELETE may result in a 404 NOT FOUND being returned.
        Finally, from the client side, for the majority of our APIs, two subsequent PUTs will not work due to the status key; you must do PUT GET PUT
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

    def __init__(self, token: Optional[str] = None, prefix_url: str = API_URL, **kwargs: Any):
        """
        Create a new merq session using token (the API Key)
        """
        self.session_args = kwargs
        self.token = token

        self._session: Optional[Session] = None
        self._session_pid: int = -1
        self._prefix_url = prefix_url
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
        url: str,
        params: dict[str, Any] | None = None,
        data: Any = None,
        headers: dict[str, str] | None = None,
        options: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> Response:
        """
        Perform an http request with this session
        request session helpers sess.put, sess.get, etc, call this

        Note: urljoin has some perhaps non obvious behavior:

            In [2]: from urllib.parse import urljoin

            In [3]: urljoin("https://localhost:8080", "resource")
            Out[3]: 'https://localhost:8080/resource'

            In [4]: urljoin("https://localhost:8080", "/resource")
            Out[4]: 'https://localhost:8080/resource'

            In [5]: urljoin("https://localhost:8080/", "/resource")
            Out[5]: 'https://localhost:8080/resource'

            In [6]: urljoin("https://localhost:8080", "//resource")
            Out[6]: 'https://resource' # ??
        """
        assert params is None or options is None, "both params and options cannot be passed"
        if url.startswith("//"):
            logger.warning(f"URL {url} starts with //, this is probably a mistake")

        headers = deepcopy(headers) or {}  # do not modify client dict
        if self.token:
            headers["Authorization"] = f"{self.token_type} {self.token}"

        options_st = "" if not options else ("?" + "&".join([f"{k}={v}" for k, v in options.items()]))
        url = urljoin(self._prefix_url, url)
        logger.debug(f"Performing {method} on {url}{options_st}")
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
        req_id_prefix: str | None = MERQ_CLIENT_PREFIX,
        **kwargs: Any,
    ):
        """
        Can specify your own oauth token,default is no token (only public APIs)

        req_id_prefix: if no request id is explicitly passed in any function call (get,post etc), and this is set, this prefix will be used with a uuid4.hex to generate a request id
        This is useful for aggregating server side logs for different sources of calls - eg requests generated from merqube.com vs this CLI can easily be distinguished
        It defaults to a constant.
        You can remove the prefix by explcitly setting None and the server will generate (and return) one, though there is not a great reason to do that..
        """
        super().__init__(token=token, **kwargs)
        self._req_id_prefix = req_id_prefix

    def handle_nonrecoverable(self, res: Response, exc: Exception, req_id: str) -> None:
        """helper function that handles a non recoverable error"""
        logger.exception(exc)
        try:
            # we may not have a json depending on the response
            rj = res.json()
        except (AttributeError, json.decoder.JSONDecodeError):
            rj = {}
        logger.error(f"Request failed with status {res.status_code}: {rj}. Request ID: {req_id}")
        raise APIError(code=res.status_code, response_json=rj, request_id=req_id)

    def request_raise(self, method: httpm, url: str, **kwargs: Any) -> Response:
        """request method that logs the status code and raises on non 2XX"""

        # Generate a new requestid if this call isnt being made in a chain that already has it.
        # (eg client calls dataapi, dataapi calls secapi - we dont want the second call to overwrite the original)
        # if this isnt set by a client making a call to one of our APIs, the API itself will generate one (eg customer call)
        # order is: 1) explicitly specified 2) set via chain, 3) generate new
        headers = deepcopy(kwargs.pop("headers", {})) or {}
        if REQUEST_ID_HEADER not in headers or not headers[REQUEST_ID_HEADER]:
            if (from_env := os.getenv(MERQ_REQUEST_ID_ENV_VAR)) is not None:
                headers[REQUEST_ID_HEADER] = from_env
            elif rip := self._req_id_prefix:
                headers[REQUEST_ID_HEADER] = f"{rip}_{uuid.uuid4().hex}"
            else:  # do not allow explicit None or ""
                headers.pop(REQUEST_ID_HEADER, None)

        res = self.request(method=method, url=url, headers=headers, **kwargs)
        try:
            res.raise_for_status()
        except HTTPError as e:
            self.handle_nonrecoverable(res=res, exc=e, req_id=res.headers.get(REQUEST_ID_HEADER, ""))

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

    def get_collection(
        self, url: str, options: Optional[dict[str, Any]] = None, raise_perm_errors: bool = False, **kwargs: Any
    ) -> list[Any]:
        """get the inner results array from a collection API"""
        res = self.get(url, options=options, **kwargs).json()

        if PERMISSION_ERROR_RES in res.get("error_codes", []) and raise_perm_errors:
            raise PermissionError("This session does not have permission to view some or all of this data")

        return cast(list[Any], res["results"])

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
            logger.error(f"Expected 1 result but {num_results} found!")
            if num_results == 0:
                raise APIError(404, {"message": "No results found for url {url} but 1 was expected!"})
            raise APIError(409, {"message": f"Only one result was expected but multiple ({num_results}) found!"})
        return res[0]


@cached(cache=LRUCache(maxsize=256))
def get_merqube_session(
    token: str | None = None, req_id_prefix: str = MERQ_CLIENT_PREFIX, **session_args: Any
) -> MerqubeAPISession:
    """
    Cached; returns a session with the given token
    """
    return MerqubeAPISession(token=token, req_id_prefix=req_id_prefix, **session_args)
