"""Amber Electric Pricing API"""

import logging
from datetime import datetime

_LOGGER = logging.getLogger(__name__)
_AMBER_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class Price(object):
    def __init__(self, protocol=None):
        super().__init__()
        self.__protocol = protocol

    async def update(self):
        data = {"headers": {"normalizedNames": {}, "lazyUpdate": None, "headers": {}}}
        response = await self.__protocol.api_post(path="Price/GetPriceList", json=data)
        if not (response and "data" in response):
            return None
        self.__current = CurrentPrice(response["data"])
        self.__forecast = ForecastPrices(response["data"])
        return self

    @property
    def current(self):
        try:
            return self.__current
        except AttributeError:
            return None

    @property
    def forecast(self):
        try:
            return self.__forecast
        except AttributeError:
            return None


class ForecastPrices(object):
    def __init__(self, price_payload):
        super().__init__()
        self.__prices = dict()
        if "forecastPrices" in price_payload:
            for forecast in price_payload["forecastPrices"]:
                price = ForecastPrice(forecast)
                if price and price.ts:
                    self.__prices[price.ts] = price

    @property
    def list(self):
        try:
            unsorted = self.__prices
        except AttributeError:
            return None
        if not unsorted:
            return None

        data = list()
        for i in sorted(self.__prices.keys()):
            data.append(self.__prices[i])

        return data


class PriceData(object):
    def __init__(self, price_payload):
        super().__init__()
        if "currentPriceKWH" in price_payload:
            self.__price_kwh = float(price_payload["currentPriceKWH"])
        elif "priceKWH" in price_payload:
            self.__price_kwh = float(price_payload["priceKWH"])
        else:
            self.__price_kwh = None

        if "currentRenewableInGrid" in price_payload:
            self.__renewable = float(float(price_payload["currentRenewableInGrid"]))
        elif "renewableInGrid" in price_payload:
            self.__renewable = float(float(price_payload["renewableInGrid"]))
        else:
            self.__renewable = None

        if "currentPriceColor" in price_payload:
            self.__color = price_payload["currentPriceColor"]
        elif "color" in price_payload:
            self.__color = price_payload["color"]
        else:
            self.__color = None

        if "currentPricePeriod" in price_payload:
            self.__period = datetime.strptime(
                price_payload["currentPricePeriod"], _AMBER_DATETIME_FORMAT
            )
        elif "period" in price_payload:
            self.__period = datetime.strptime(
                price_payload["period"], _AMBER_DATETIME_FORMAT
            )
        else:
            self.__period = None

    @property
    def ts(self):
        try:
            return self.__period.timestamp()
        except AttributeError:
            return None

    @property
    def period(self):
        try:
            return self.__period
        except AttributeError:
            return None

    @property
    def kwh(self):
        try:
            return round(self.__price_kwh, 2)
        except AttributeError:
            return None

    @property
    def renewable(self):
        try:
            return round(self.__renewable / 100, 2)
        except AttributeError:
            return None

    @property
    def color(self):
        try:
            return self.__color.lower()
        except AttributeError:
            return None

    @property
    def emoji(self):
        if self.color == "red":
            return "🔴"
        elif self.color == "yellow":
            return "🟡"
        elif self.color == "green":
            return "🟢"
        else:
            return "🤷"


class CurrentPrice(PriceData):
    pass


class ForecastPrice(PriceData):
    pass