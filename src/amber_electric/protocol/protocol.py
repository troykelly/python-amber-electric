"""Handle communications with the Amber Electric API"""

import asyncio
import backoff
import logging
import requests

from ..exceptions import AmberElectricAPIError, AmberElectricAuthenticationFailed
from ..auth import auth as AmberAuth

_LOGGER = logging.getLogger(__name__)
logging.getLogger("backoff").addHandler(logging.StreamHandler())

_DEFAULT_HOST = "api-bff.amberelectric.com.au"
_DEFAULT_VERSION = "1.0"

_REFRENCE = "https://github.com/troykelly/python-amber-electric"
"""Used to identify this to Amber Electric API"""

_USER_AGENT = f"Mozilla/5.0 (compatible; Aperim; +{_REFRENCE})"
"""The User Agent for Amber Electric API calls"""

_FORCE_ORIGIN = "https://app.amberelectric.com.au"


def fatal_code(e):
    return 400 <= e.response.status_code < 500


class Protocol(object):
    def __init__(self, username=None, password=None, loop=None):
        super().__init__()
        self.__host = _DEFAULT_HOST
        self.__version = _DEFAULT_VERSION
        self.__username = username
        self.__password = password
        self.__loop = loop if loop else asyncio.get_event_loop()

        self.__api_url = f"https://{self.__host}/api/v{self.__version}"

        self.__session = None

    async def auth(self):
        auth_response = await AmberAuth(
            protocol=self, username=self.__username, password=self.__password
        )
        if not auth_response:
            raise AmberElectricAuthenticationFailed(
                message="Failed to authenticate with API"
            )
        self.__auth = auth_response
        return self.__auth

    def logout(self):
        self.__session = None
        self.__auth = None

    async def api_get(self, path=None, params=None, headers=None):
        """Make a GET request to the Amber Electric API

        Attributes:
            path (str): The path to the endpoint
            params (str): Any URL paramaters to pass
            headers (dict): Headers to be sent in the request
        """

        if path:
            if not path.startswith("/"):
                path = f"/{path}"
        else:
            path = ""

        url = f"{self.__api_url}{path}"
        return await self.__loop.run_in_executor(
            None, self.__request, "GET", url, params, None, headers
        )

    async def api_post(self, path=None, params=None, json=None, headers=None):
        """Make a POST request to the Amber Electric API

        Attributes:
            path (str): The path to the endpoint
            params (str): Any URL paramaters to pass
            json (str): JSON to be passed in the body
            headers (dict): Headers to be sent in the request
        """

        if path:
            if not path.startswith("/"):
                path = f"/{path}"
        else:
            path = ""

        url = f"{self.__api_url}{path}"
        return await self.__loop.run_in_executor(
            None, self.__request, "POST", url, params, json, headers
        )

    async def api_put(self, path=None, params=None, json=None, headers=None):
        """Make a PUT request to the Amber Electric API

        Attributes:
            path (str): The path to the endpoint
            params (str): Any URL paramaters to pass
            json (str): JSON to be passed in the body
            headers (dict): Headers to be sent in the request
        """

        if path:
            if not path.startswith("/"):
                path = f"/{path}"
        else:
            path = ""

        url = f"{self.__api_url}{path}"
        return await self.__loop.run_in_executor(
            None, self.__request, "PUT", url, params, json, headers
        )

    async def api_delete(self, path=None, params=None, json=None, headers=None):
        """Make a DELETE request to the Amber Electric API

        Attributes:
            path (str): The path to the endpoint
            params (str): Any URL paramaters to pass
            json (str): JSON to be passed in the body
            headers (dict): Headers to be sent in the request
        """

        if path:
            if not path.startswith("/"):
                path = f"/{path}"
        else:
            path = ""

        url = f"{self.__api_url}{path}"
        return await self.__loop.run_in_executor(
            None, self.__request, "DELETE", url, params, json, headers
        )

    def __get_session(self):
        if self.__session:
            return self.__session
        self.__session = requests.session()
        session_headers = {
            "User-Agent": _USER_AGENT,
            "Referer": _REFRENCE,
            "Origin": _FORCE_ORIGIN,
            "Content-Type": "application/json",
        }
        self.__session.headers = session_headers
        return self.__session

    @backoff.on_exception(
        backoff.fibo,
        AmberElectricAPIError,
        max_time=300,
        giveup=fatal_code,
    )
    def __request(self, method="GET", url=None, params=None, json=None, headers=None):

        _LOGGER.debug(
            {
                "url": url,
                "params": params,
                "data": json,
                "headers": headers,
            }
        )

        session = self.__get_session()

        if not headers:
            headers = {}

        id_token = getattr(self.__auth, "id_token", None)
        refresh_token = getattr(self.__auth, "refresh_token", None)
        if id_token:
            headers["Authorization"] = id_token
        if refresh_token:
            headers["RefreshToken"] = refresh_token

        try:
            response = session.request(
                method, url, params=params, json=json, headers=headers
            )
        except Exception as err:
            raise AmberElectricAPIError(
                message="Unkown error from Amber Electric API", exception=err
            )

        status_code = getattr(response, "status_code", None)

        try:
            data = response.json()
        except:
            data = None

        if not status_code:
            raise AmberElectricAPIError(
                message="Amber Electric API failed to repond.", response=response
            )

        success = 200 <= response.status_code <= 299

        if response.status_code == 401 or response.status_code == 403:
            raise AmberElectricAPIError(
                message="Amber Electric API Access Denied",
                response=response,
            )

        if not success:
            raise AmberElectricAPIError(
                message="Amber Electric API Error",
                response=response,
            )

        return data
