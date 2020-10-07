# Python Library for Amber Electric API

![PyPI](https://github.com/troykelly/python-amber-electric/workflows/Publish%20Python%20%F0%9F%90%8D%20distributions%20%F0%9F%93%A6%20to%20PyPI%20and%20TestPyPI/badge.svg?branch=main) [![GitHub issues](https://img.shields.io/github/issues/troykelly/python-amber-electric?style=plastic)](https://github.com/troykelly/python-amber-electric/issues) [![GitHub forks](https://img.shields.io/github/forks/troykelly/python-amber-electric?style=plastic)](https://github.com/troykelly/python-amber-electric/network) [![GitHub stars](https://img.shields.io/github/stars/troykelly/python-amber-electric?style=plastic)](https://github.com/troykelly/python-amber-electric/stargazers) [![GitHub license](https://img.shields.io/github/license/troykelly/python-amber-electric?style=plastic)](https://github.com/troykelly/python-amber-electric/blob/main/LICENSE.txt) [![Twitter](https://img.shields.io/twitter/url?style=social&url=https%3A%2F%2Fgithub.com%2Ftroykelly%2Fpython-amber-electric)](https://twitter.com/intent/tweet?url=https%3A%2F%2Fgithub.com%2Ftroykelly%2Fpython-amber-electric&via=troykelly&text=Access%20the%20Constellix%20DNS%20API%20From%20Python&hashtags=%23python%20%23devops%20%23dns%20%23api)

## Description

Connects to the [Amber Electric API](https://amberelectric.com.au) and retrieves market, usage and pricing information

### Note

This is in no way affiliated with Amber Electric.

### Issues

I don't know what the usage data for an account looks like at the moment.
Until I have an account with active usage data - this part of the API is going to be very light.

### Logging / Debugging

This library uses `logging` just set the log level and format you need.

## Example

### See current market pricing

```python
from amber_electric import AmberElectric

api = AmberElectric(
        latitude=-37.828690,
        longitude=144.997460,
    )
print(api.market)
```

### Get your current pricing

```python
api = AmberElectric(
        latitude=-37.828690,
        longitude=144.997460,
		username="family@example.com",
		password="secret"
    )
await api.auth()
print(api.price)
```

### Get your current usage (WIP)

```python
api = AmberElectric(
        latitude=-37.828690,
        longitude=144.997460,
		username="family@example.com",
		password="secret"
    )
await api.auth()
print(api.usage)
```

## Support

<a href="https://www.buymeacoffee.com/troykelly" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>
