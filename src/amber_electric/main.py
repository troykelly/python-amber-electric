"""Amber Electric API"""
import asyncio
import os

from .protocol import Protocol
from .price import Price
from .usage import Usage
from .market import Market


class AmberElectric(object):
    def __init__(
        self,
        username=None,
        password=None,
        latitude=None,
        longitude=None,
        postcode=None,
        loop=None,
    ):
        """Amber Electric API

        Attributes:
            username (str): Amber Electric portal username
            password (str): Amber Electric portal password
            latitude (float): Location latitude for market pricing - supersedes postcode
            longitude (float): Location longitude for market pricing - supersedes postcode
            postcode (int): Location postcode for market pricing
            loop (loop): asyncio loop
        """
        super().__init__()
        self.__loop = loop if loop else asyncio.get_event_loop()
        api_username = username if username else os.environ.get("AMBER_USERNAME", None)
        api_password = password if password else os.environ.get("AMBER_PASSWORD", None)
        self.__protocol = Protocol(
            username=api_username, password=api_password, loop=loop
        )
        self.__market = Market(
            protocol=self.__protocol,
            latitude=latitude,
            longitude=longitude,
            postcode=postcode,
        )
        if api_username and api_password:
            self.__price = Price(protocol=self.__protocol)
            self.__usage = Usage(protocol=self.__protocol)

    async def auth(self):
        return await self.__protocol.auth()

    async def update(self):
        if self.__price:
            await self.__price.update()
        if self.__usage:
            await self.__usage.update()
        if self.__market:
            await self.__market.update()

    @property
    def price(self):
        try:
            return self.__price
        except AttributeError:
            return None

    @property
    def usage(self):
        try:
            return self.__usage
        except AttributeError:
            return None

    @property
    def market(self):
        try:
            return self.__market
        except AttributeError:
            return None
