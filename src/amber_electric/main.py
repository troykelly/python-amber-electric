"""Amber Electric API"""
import asyncio
from datetime import datetime, timedelta
import inspect
import logging
import os

from .protocol import Protocol
from .price import Price
from .usage import Usage
from .market import Market

_LOGGER = logging.getLogger(__name__)


class AmberElectric(object):
    """
    API Access to the Amber Electric API

    Allows for checking public and authenticated Amber Electric API endpoints.

    Attributes
    ----------
    price : object
        specific pricing for the authnticated account (only available once authenticated)
    usage : object
        account usage (only available once authenticated)
    market : object
        public market pricing and consumption data

    Methods
    -------
    auth()
        Authenticate against the API
    update()
        Updates price, usage and market data
    """

    def __init__(
        self,
        username=None,
        password=None,
        latitude=None,
        longitude=None,
        postcode=None,
        loop=None,
    ):
        """
        Parameters
        ----------
        username : str, optional
            Amber Electric portal username
        password : str, optional
            Amber Electric portal password
        latitude : float, optional
            Location latitude for market pricing - supersedes postcode
        longitude : float, optional
            Location longitude for market pricing - supersedes postcode
        postcode : int, optional
            Location postcode for market pricing
        """

        super().__init__()
        self.__loop = loop if loop else asyncio.get_event_loop()
        self.__poll_complete_push = list()
        self.__polling_active = False
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

    async def __poll_for_updates(self, interval_delta):
        self.__polling_active = True
        while True:
            _LOGGER.debug("Polling for updates...")
            await self.update()
            if self.__poll_complete_push:
                data = dict()
                data["ts"] = datetime.now().timestamp()
                data["postcode"] = self.__market.postcode
                data["address"] = self.__market.address
                data["polled"] = True
                if self.__price:
                    data["price"] = self.__price
                if self.__usage:
                    data["usage"] = self.__usage
                if self.__market:
                    data["market"] = self.__market
                for poll_complete_push in self.__poll_complete_push:
                    function_name = poll_complete_push.__name__
                    _LOGGER.debug(f"Sending update to {function_name}")
                    try:
                        if asyncio.iscoroutinefunction(poll_complete_push):
                            await poll_complete_push(data)
                        else:
                            poll_complete_push(data)
                    except Exception as err:
                        _LOGGER.exception(err)
            await asyncio.sleep(interval_delta.total_seconds())

    def poll_for_updates(self, interval=60, event_receiver=None):
        if not self.__protocol.loop:
            return None

        if not interval:
            interval = timedelta(seconds=60)

        if not isinstance(interval, timedelta):
            interval = timedelta(seconds=interval)

        if event_receiver and not event_receiver in self.__poll_complete_push:
            self.__poll_complete_push.append(event_receiver)

        if self.__polling_active:
            _LOGGER.warning("Already polling for updates. Not duplicating.")
            return None

        _LOGGER.debug(
            "Checking for updates every %d seconds...", interval.total_seconds()
        )

        task = self.__protocol.loop.create_task(
            self.__poll_for_updates(interval_delta=interval)
        )
        return task

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

    @property
    def postcode(self):
        try:
            return self.__market.postcode
        except AttributeError:
            return None

    @property
    def address(self):
        try:
            return self.__market.address
        except AttributeError:
            return None
