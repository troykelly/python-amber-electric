"""Amber Electric Usage"""

import logging
from datetime import datetime

_LOGGER = logging.getLogger(__name__)
_AMBER_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class Usage(object):
    def __init__(self, protocol=None):
        super().__init__()
        self.__protocol = protocol

    async def update(self):
        data = {"headers": {"normalizedNames": {}, "lazyUpdate": null, "headers": {}}}
        response = await self.__protocol.api_post(
            path="UsageHub/GetUsageForHub", json=data
        )
        if not (response and "data" in response):
            return None
        _LOGGER.debug(response["data"])
        return self
