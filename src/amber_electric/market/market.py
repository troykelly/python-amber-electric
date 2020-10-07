"""Amber Electric Market Price API"""


from datetime import datetime, timedelta
import json
import logging
import re

from ..exceptions import NoLocationError
from ..geocode import reverse_geocode, Point

_LOGGER = logging.getLogger(__name__)
_AMBER_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
_NEM_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
_NEM_TZ_OFFSET = "+1000"
_NEM_SETTLEMENT_PERIOD = timedelta(minutes=30)

_TAX_GST_OFFSET = 0.1

_RE_AMBER_PERIOD_TYPE = re.compile(
    r"(?:(?P<seconds>^\d+)SEC$)|(?:(?P<minutes>^\d+)MIN$)|(?:(?P<hours>^\d+)HOUR$)|(?:(?P<days>^\d+)DAY$)"
)


class Market(object):
    def __init__(self, protocol=None, postcode=None, latitude=None, longitude=None):
        super().__init__()
        self.__protocol = protocol
        self.__postcode = int(postcode) if postcode else None
        self.__address = None
        if latitude and longitude:
            self.__point = Point(latitude, longitude)
        else:
            self.__point = None

    async def update(self):
        if self.__point and not self.__address:
            self.__address = await reverse_geocode(self.__point, self.__protocol.loop)
            if not (
                self.__address.postcode
                and self.__address.country.upper() == "AUSTRALIA"
            ):
                raise NoLocationError(
                    message="Address unsuitable - must be in Australia and have a postcode.",
                    address=self.__address,
                )

        if not self.postcode:
            raise NoLocationError(message="No postcode availabile")

        data = {"postcode": f"{self.postcode:04}"}
        response = await self.__protocol.raw(
            method="POST",
            url="https://api.amberelectric.com.au/prices/listprices",
            json=data,
        )
        if not (response and "data" in response):
            return None
        self.__variable = VariablePeriodData(response["data"])
        if "currentNEMtime" in response["data"]:
            self.__nemtime = datetime.strptime(
                response["data"]["currentNEMtime"] + _NEM_TZ_OFFSET,
                _NEM_DATETIME_FORMAT,
            )
        self.__network_provider = (
            response["data"]["networkProvider"]
            if "networkProvider" in response["data"]
            else None
        )
        if "staticPrices" in response["data"]:
            if "E1" in response["data"]["staticPrices"]:
                self.__e1 = E1(response["data"]["staticPrices"]["E1"])
            if "E2" in response["data"]["staticPrices"]:
                self.__e2 = E2(response["data"]["staticPrices"]["E2"])
            if "B1" in response["data"]["staticPrices"]:
                self.__b1 = B1(response["data"]["staticPrices"]["B1"])
            if "E1TOU" in response["data"]["staticPrices"]:
                self.__e1tou = E2(response["data"]["staticPrices"]["E1TOU"])

        return self

    @property
    def postcode(self):
        if (
            self.__address
            and self.__address.postcode
            and self.__address.country.upper() == "AUSTRALIA"
        ):
            return int(self.__address.postcode)
        else:
            return self.__postcode

    @property
    def address(self):
        try:
            return self.__address
        except AttributeError:
            return None

    @property
    def current_period(self):
        now = datetime.now()
        delta = timedelta(minutes=30)
        return now + (datetime.min - now) % delta

    @property
    def current_variable(self):
        current_period_ts = self.current_period.timestamp()
        return self.__variable.get_period(current_period_ts)

    @property
    def variable(self):
        try:
            return self.__variable
        except AttributeError:
            return None

    @property
    def e1(self):
        try:
            return self.__e1
        except AttributeError:
            return None

    @property
    def e2(self):
        try:
            return self.__e2
        except AttributeError:
            return None

    @property
    def b1(self):
        try:
            return self.__b1
        except AttributeError:
            return None

    @property
    def e1tou(self):
        try:
            return self.__e1tou
        except AttributeError:
            return None

    @property
    def usage_price(self):
        if not (self.e1 and self.variable):
            return None
        variable_data = self.current_variable
        if not variable_data:
            return None
        fixed_kwh_price = self.e1.total_fixed_kwh_price
        loss_factor = self.e1.loss_factor
        wholesale_kwh_price = variable_data.wholesale_kwh_price
        if not (fixed_kwh_price and loss_factor and wholesale_kwh_price):
            return None
        price = fixed_kwh_price + (loss_factor * wholesale_kwh_price)
        return price

    @property
    def export_price(self):
        if not (self.e1 and self.variable):
            return None
        variable_data = self.current_variable
        if not variable_data:
            return None
        fixed_kwh_price = self.b1.total_fixed_kwh_price
        loss_factor = self.b1.loss_factor
        wholesale_kwh_price = variable_data.wholesale_kwh_price
        if not (fixed_kwh_price and loss_factor and wholesale_kwh_price):
            return None
        price = fixed_kwh_price + (loss_factor * wholesale_kwh_price)
        return price

    @property
    def network_provider(self):
        try:
            return self.__network_provider
        except AttributeError:
            return None

    @property
    def nem_time(self):
        try:
            return self.__nemtime
        except AttributeError:
            return None

    @property
    def nem_ts(self):
        try:
            return self.__nemtime.timestamp()
        except AttributeError:
            return None

    def __repr__(self):
        data = dict()
        data["postcode"] = self.postcode
        data["nem_time"] = self.__nemtime.isoformat()
        data["nem_ts"] = self.__nemtime.timestamp()
        data["current_period"] = self.current_period.isoformat()
        data["current_period_ts"] = self.current_period.timestamp()
        if self.usage_price:
            data["usage_price"] = self.usage_price
        if self.export_price:
            data["export_price"] = self.export_price
        data["network_provider"] = self.__network_provider
        data["variable"] = dict()
        data["static"] = dict()
        if self.e1:
            data["static"]["e1"] = self.e1.__repr__()
        if self.e2:
            data["static"]["e2"] = self.e2.__repr__()
        if self.b1:
            data["static"]["b1"] = self.b1.__repr__()
        if self.e1tou:
            data["static"]["e1tou"] = self.e1tou.__repr__()
        data["variable"]["periods"] = list()
        for period in self.variable.periods:
            data["variable"]["periods"].append(period.__repr__())
        return data

    def __str__(self):
        return json.dumps(self.__repr__(), sort_keys=True, indent=4)


class VariablePeriodData(object):
    def __init__(self, prices_payload):
        super().__init__()
        self.__periods = dict()
        if "variablePricesAndRenewables" in prices_payload:
            for variable_price_payload in prices_payload["variablePricesAndRenewables"]:
                variable_period = VariablePeriod(variable_price_payload)
                if variable_period.ts:
                    self.__periods[variable_period.ts] = variable_period

    def get_period(self, period_ts):
        if period_ts in self.__periods:
            return self.__periods[period_ts]
        return None

    @property
    def periods(self):
        try:
            unsorted = self.__periods
        except AttributeError:
            return None
        if not unsorted:
            return None

        data = list()
        for i in sorted(self.__periods.keys()):
            data.append(self.__periods[i])
        return data

    def __repr__(self):
        data = dict()
        data["periods"] = list()
        for i in sorted(self.__periods.keys()):
            data["periods"].append(self.__periods[i])
        return data

    def __str__(self):
        return json.dumps(self.__repr__(), sort_keys=True, indent=4)


class VariablePeriod(object):
    def __init__(self, price_payload):
        super().__init__()

        if not "period" in price_payload:
            _LOGGER.error(price_payload)
            raise AttributeError("Period must be supplied and valid")

        period_source_data = price_payload["periodSource"].upper()
        period_source = _RE_AMBER_PERIOD_TYPE.search(period_source_data)
        if period_source:
            period_source_dict = period_source.groupdict()
            self.__period_delta = timedelta(
                days=int(period_source_dict["days"])
                if period_source_dict["days"]
                else 0,
                hours=int(period_source_dict["hours"])
                if period_source_dict["hours"]
                else 0,
                minutes=int(period_source_dict["minutes"])
                if period_source_dict["minutes"]
                else 0,
                seconds=int(period_source_dict["seconds"])
                if period_source_dict["seconds"]
                else 0,
            )

        self.__period_end = datetime.strptime(
            price_payload["period"] + _NEM_TZ_OFFSET, _NEM_DATETIME_FORMAT
        )

        self.__period_type = (
            price_payload["periodType"] if "periodType" in price_payload else None
        )
        self.__semi_scheduled_generation = (
            float(price_payload["semiScheduledGeneration"])
            if "semiScheduledGeneration" in price_payload
            else None
        )
        self.__operational_demand = (
            float(price_payload["operationalDemand"])
            if "operationalDemand" in price_payload
            else None
        )
        self.__rooftop_solar = (
            float(price_payload["rooftopSolar"])
            if "rooftopSolar" in price_payload
            else None
        )
        self.__created_at = (
            datetime.strptime(
                price_payload["createdAt"] + _NEM_TZ_OFFSET, _NEM_DATETIME_FORMAT
            )
            if "createdAt" in price_payload
            else None
        )
        self.__wholesale_kwh_price = (
            float(price_payload["wholesaleKWHPrice"])
            if "wholesaleKWHPrice" in price_payload
            else None
        )
        self.__region = price_payload["region"] if "region" in price_payload else None
        self.__renewables_percentage = (
            float(price_payload["renewablesPercentage"])
            if "renewablesPercentage" in price_payload
            else None
        )

        self.__percentile_rank = (
            float(price_payload["percentileRank"])
            if "percentileRank" in price_payload
            else None
        )

    # TODO: Deprecate this
    @property
    def ts(self):
        try:
            return self.period_end.timestamp()
        except AttributeError:
            return None

    @property
    def ts_end(self):
        try:
            return self.period_end.timestamp()
        except AttributeError:
            return None

    @property
    def ts_start(self):
        try:
            return self.period_start.timestamp()
        except AttributeError:
            return None

    @property
    def period_type(self):
        try:
            return self.__period_type
        except AttributeError:
            return None

    @property
    def semi_scheduled_generation(self):
        try:
            return self.__semi_scheduled_generation
        except AttributeError:
            return None

    @property
    def operational_demand(self):
        try:
            return self.__operational_demand
        except AttributeError:
            return None

    @property
    def rooftop_solar(self):
        try:
            return self.__rooftop_solar
        except AttributeError:
            return None

    @property
    def created_at(self):
        try:
            return self.__created_at
        except AttributeError:
            return None

    @property
    def wholesale_kwh_price(self):
        try:
            return self.__wholesale_kwh_price / 100 / (1 + _TAX_GST_OFFSET)
        except AttributeError:
            return None

    @property
    def region(self):
        try:
            return self.__region
        except AttributeError:
            return None

    @property
    def period_end(self):
        try:
            return self.__period_end
        except AttributeError:
            return None

    @property
    def period_start(self):
        try:
            period_end = self.__period_end
            period_delta = _NEM_SETTLEMENT_PERIOD
        except AttributeError:
            return None

        if not (period_end and period_delta):
            return None

        return period_end - period_delta + timedelta(milliseconds=1)

    @property
    def renewables_percentage(self):
        try:
            return self.__renewables_percentage
        except AttributeError:
            return None

    # TODO: Deprecate this
    @property
    def period_source(self):
        try:
            return self.__period_delta
        except AttributeError:
            return None

    @property
    def period_delta(self):
        try:
            return self.__period_delta
        except AttributeError:
            return None

    @property
    def percentile_rank(self):
        try:
            return self.__percentile_rank
        except AttributeError:
            return None

    def __repr__(self):
        data = {}
        data["ts_end"] = self.ts_end
        data["ts_start"] = self.ts_start
        data["period_start"] = self.period_start.isoformat()
        data["period_end"] = self.period_end.isoformat()
        data["period_type"] = self.period_type
        data["semi_scheduled_generation"] = self.semi_scheduled_generation
        data["operational_demand"] = self.operational_demand
        data["rooftop_solar"] = self.rooftop_solar
        if self.created_at:
            data["created_at"] = self.created_at.isoformat()
        data["wholesale_kwh_price"] = self.wholesale_kwh_price
        data["region"] = self.region
        data["renewables_percentage"] = self.renewables_percentage
        if self.period_delta:
            data["period_delta"] = self.period_delta.total_seconds()
        data["percentile_rank"] = self.percentile_rank
        return data

    def __str__(self):
        return json.dumps(self.__repr__(), sort_keys=True, indent=4)


class PriceData(object):
    def __init__(
        self, price_payload, current_time=None, postcode=None, network_provider=None
    ):
        super().__init__()
        if "dataAvailable" in price_payload:
            self.__data_available = price_payload["dataAvailable"]

        if "networkDailyPrice" in price_payload:
            self.__network_daily_price = float(price_payload["networkDailyPrice"])

        if "basicMeterDailyPrice" in price_payload:
            self.__basic_meter_daily_price = float(
                price_payload["basicMeterDailyPrice"]
            )

        if "additionalSmartMeterDailyPrice" in price_payload:
            self.__additional_smart_meter_daily_price = float(
                price_payload["additionalSmartMeterDailyPrice"]
            )

        if "amberDailyPrice" in price_payload:
            self.__amber_daily_price = float(price_payload["amberDailyPrice"])

        if "totalDailyPrice" in price_payload:
            self.__total_daily_price = float(price_payload["totalDailyPrice"])

        if "networkKWHPrice" in price_payload:
            self.__network_kwh_price = float(price_payload["networkKWHPrice"])

        if "marketKWHPrice" in price_payload:
            self.__market_kwh_price = float(price_payload["marketKWHPrice"])

        if "greenKWHPrice" in price_payload:
            self.__green_kwh_price = float(price_payload["greenKWHPrice"])

        if "carbonNeutralKWHPrice" in price_payload:
            self.__carbon_neutral_kwh_price = float(
                price_payload["carbonNeutralKWHPrice"]
            )

        if "lossFactor" in price_payload:
            self.__loss_factor = float(price_payload["lossFactor"])

        if "offsetKWHPrice" in price_payload:
            self.__offset_kwh_price = float(price_payload["offsetKWHPrice"])

        if "totalfixedKWHPrice" in price_payload:
            self.__total_fixed_kwh_price = float(price_payload["totalfixedKWHPrice"])

        if "totalBlackPeakFixedKWHPrice" in price_payload:
            self.__total_black_peak_fixed_kwh_price = float(
                price_payload["totalBlackPeakFixedKWHPrice"]
            )

        if "totalBlackShoulderFixedKWHPrice" in price_payload:
            self.__total_black_shoulder_fixed_kwh_price = float(
                price_payload["totalBlackShoulderFixedKWHPrice"]
            )

        if "totalBlackOffpeakFixedKWHPrice" in price_payload:
            self.__total_black_offpeak_fixed_kwh_price = float(
                price_payload["totalBlackOffpeakFixedKWHPrice"]
            )

    @property
    def data_available(self):
        try:
            return self.__data_available
        except AttributeError:
            return None

    @property
    def network_daily_price(self):
        try:
            return self.__network_daily_price / 100 / (1 + _TAX_GST_OFFSET)
        except AttributeError:
            return None

    @property
    def basic_meter_daily_price(self):
        try:
            return self.__basic_meter_daily_price / 100 / (1 + _TAX_GST_OFFSET)
        except AttributeError:
            return None

    @property
    def additional_smart_meter_daily_price(self):
        try:
            return (
                self.__additional_smart_meter_daily_price / 100 / (1 + _TAX_GST_OFFSET)
            )
        except AttributeError:
            return None

    @property
    def amber_daily_price(self):
        try:
            return self.__amber_daily_price / 100 / (1 + _TAX_GST_OFFSET)
        except AttributeError:
            return None

    @property
    def total_daily_price(self):
        try:
            return self.__total_daily_price / 100 / (1 + _TAX_GST_OFFSET)
        except AttributeError:
            return None

    @property
    def network_kwh_price(self):
        try:
            return self.__network_kwh_price / 100 / (1 + _TAX_GST_OFFSET)
        except AttributeError:
            return None

    @property
    def market_kwh_price(self):
        try:
            return self.__market_kwh_price / 100 / (1 + _TAX_GST_OFFSET)
        except AttributeError:
            return None

    @property
    def green_kwh_price(self):
        try:
            return self.__green_kwh_price / 100 / (1 + _TAX_GST_OFFSET)
        except AttributeError:
            return None

    @property
    def carbon_neutral_kwh_price(self):
        try:
            return self.__carbon_neutral_kwh_price / 100 / (1 + _TAX_GST_OFFSET)
        except AttributeError:
            return None

    @property
    def loss_factor(self):
        try:
            return self.__loss_factor
        except AttributeError:
            return None

    @property
    def offset_kwh_price(self):
        try:
            return self.__offset_kwh_price / 100 / (1 + _TAX_GST_OFFSET)
        except AttributeError:
            return None

    @property
    def total_fixed_kwh_price(self):
        try:
            return self.__total_fixed_kwh_price / 100 / (1 + _TAX_GST_OFFSET)
        except AttributeError:
            return None

    @property
    def total_black_peak_fixed_kwh_price(self):
        try:
            return self.__total_black_peak_fixed_kwh_price / 100 / (1 + _TAX_GST_OFFSET)
        except AttributeError:
            return None

    @property
    def total_black_shoulder_fixed_kwh_price(self):
        try:
            return (
                self.__total_black_shoulder_fixed_kwh_price
                / 100
                / (1 + _TAX_GST_OFFSET)
            )
        except AttributeError:
            return None

    @property
    def total_black_offpeak_fixed_kwh_price(self):
        try:
            return (
                self.__total_black_offpeak_fixed_kwh_price / 100 / (1 + _TAX_GST_OFFSET)
            )
        except AttributeError:
            return None

    def __repr__(self):
        data = dict()
        data["data_available"] = self.data_available
        data["network_daily_price"] = self.network_daily_price
        data["basic_meter_daily_price"] = self.basic_meter_daily_price
        data[
            "additional_smart_meter_daily_price"
        ] = self.additional_smart_meter_daily_price
        data["amber_daily_price"] = self.amber_daily_price
        data["total_daily_price"] = self.total_daily_price
        data["network_kwh_price"] = self.network_kwh_price
        data["market_kwh_price"] = self.market_kwh_price
        data["green_kwh_price"] = self.green_kwh_price
        data["carbon_neutral_kwh_price"] = self.carbon_neutral_kwh_price
        data["loss_factor"] = self.loss_factor
        data["offset_kwh_price"] = self.offset_kwh_price
        data["total_fixed_kwh_price"] = self.total_fixed_kwh_price
        data["total_black_peak_fixed_kwh_price"] = self.total_black_peak_fixed_kwh_price
        data[
            "total_black_shoulder_fixed_kwh_price"
        ] = self.total_black_shoulder_fixed_kwh_price
        data[
            "total_black_offpeak_fixed_kwh_price"
        ] = self.total_black_offpeak_fixed_kwh_price
        return data

    def __str__(self):
        return json.dumps(self.__repr__(), sort_keys=True, indent=4)


class E1(PriceData):
    pass


class E2(PriceData):
    pass


class B1(PriceData):
    pass


class E1TOU(PriceData):
    pass