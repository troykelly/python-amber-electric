"""Handle authentication and refresh with the
Amber Electric API
"""

from ..exceptions import AmberElectricAPIError

__PROTOCOL = None
__USERNAME = None
__PASSWORD = None


async def auth(protocol=None, username=None, password=None):
    """Authentication against the Amber Electric API

    Attributes:
        protocol (object): The protocol object
        username (string): The username to be used in authentication
        password (string): The password to be used in authentication

    Returns:
        success (boolean): The authentication state
    """
    if protocol is not None:
        __PROTOCOL = protocol

    if username is not None:
        __USERNAME = username

    if password is not None:
        __PASSWORD = password

    if not __PROTOCOL:
        raise AmberElectricAPIError(message="No connection available")

    if not (__USERNAME and __PASSWORD):
        raise AmberElectricAPIError(message="No username and password available")

    __PROTOCOL.logout()

    auth_response = await __PROTOCOL.api_post(
        path="Authentication/SignIn",
        json={
            "username": __USERNAME,
            "password": __PASSWORD,
        },
    )
    if not auth_response:
        raise AmberElectricAPIError(message="No response to API authentication request")
    return Auth(auth_response)


class Auth(object):
    def __init__(self, amber_payload=None):
        super().__init__()
        if amber_payload is not None and "data" in amber_payload:
            data = amber_payload["data"]
            self.__name = data["name"] if "name" in data else None
            self.__given_name = data["firstName"] if "firstName" in data else None
            self.__family_name = data["lastName"] if "lastName" in data else None
            self.__postcode = data["postcode"] if "postcode" in data else None
            self.__email = data["email"] if "email" in data else None
            self.__id_token = data["idToken"] if "idToken" in data else None
            self.__refresh_token = (
                data["refreshToken"] if "refreshToken" in data else None
            )
        self.service_response_type = (
            amber_payload["serviceResponseType"]
            if "serviceResponseType" in amber_payload
            else None
        )

    @property
    def id_token(self):
        try:
            return self.__id_token
        except AttributeError:
            return None

    @property
    def refresh_token(self):
        try:
            return self.__refresh_token
        except AttributeError:
            return None

    @property
    def name(self):
        try:
            return self.__name
        except AttributeError:
            return None

    @property
    def given_name(self):
        try:
            return self.__given_name
        except AttributeError:
            return None

    @property
    def family_name(self):
        try:
            return self.__family_name
        except AttributeError:
            return None
