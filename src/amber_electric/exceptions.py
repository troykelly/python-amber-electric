# -*- coding: utf-8 -*-
"""
Amber Electric API Exceptions
"""
import logging

_LOGGER = logging.getLogger(__name__)


class Error(Exception):
    """Base class for exceptions in this module."""

    pass


class NoLocationError(Error):
    """Returned when requesting market update without a postcode"""

    def __init__(self, message=None, address=None):
        super().__init__()
        self.__message = message
        self.__address = address

    @property
    def message(self):
        try:
            return self.__message
        except AttributeError:
            return None

    @property
    def address(self):
        try:
            return self.__address
        except AttributeError:
            return None


class AmberElectricAPIError(Error):
    """Returned when experiencing a general API error"""

    def __init__(self, message=None, response=None, exception=None):
        super().__init__()
        if message is not None:
            self.__message = message
        if response is not None:
            self.__response = response
        if exception is not None:
            self.__exception = exception

    @property
    def message(self):
        try:
            return self.__message
        except AttributeError:
            return None

    @property
    def response(self):
        try:
            return self.__response
        except AttributeError:
            return None

    @property
    def exception(self):
        try:
            return self.__exception
        except AttributeError:
            return None


class AmberElectricAuthenticationFailed(AmberElectricAPIError):
    pass