"""Amber Electric API"""
import asyncio
import os

from .protocol import Protocol
from .price import Price
from .usage import Usage


class AmberElectric(object):
    def __init__(self, username=None, password=None, loop=None):
        super().__init__()
        self.__loop = loop if loop else asyncio.get_event_loop()
        api_username = username if username else os.environ.get("AMBER_USERNAME", None)
        api_password = password if password else os.environ.get("AMBER_PASSWORD", None)
        self.__protocol = Protocol(
            username=api_username, password=api_password, loop=loop
        )
        self.__price = Price(protocol=self.__protocol)
        self.__usage = Usage(protocol=self.__protocol)

    async def auth(self):
        return await self.__protocol.auth()

    async def update(self):
        await self.__price.update()
        await self.__usage.update()

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
