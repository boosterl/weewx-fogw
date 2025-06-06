# ⚠ DEPRECATION NOTICE ⚠

The [weewx-gw1000](https://github.com/gjr80/weewx-gw1000) driver does the same
thing as this driver, and much more. So no need for continueing development on
this driver anymore.

# WeeWX FoGW

This is a driver for WeeWX that fetches data from Fine Offset WiFi gateways.

# Installation

## Prerequisites

This driver uses the [requests](https://github.com/psf/requests) library. This
Python package can be installed via Pip:

```
sudo pip install requests
```

Then you can clone the repo and run the installer:

```
weectl extension install weewx-fogw
```

You can then configure the driver:

```
weectl station reconfigure --driver=user.fogw --no-prompt
```

Lastly, restart WeeWX:

```
sudo systemctl restart weewx
```

# FAQ

## Why would you use this driver while the awesome [weewx-interceptor](https://github.com/matthewwall/weewx-interceptor) driver is already available? 

The Fine Offset WiFi gateways only allows to push weather data to one endpoint.
Using this driver, multiple weewx installations can fetch the same data from one
gateway. Handy if you have a weewx-installation used for testing, for example.

## Which weather stations are supported?

This driver is tested againts a [GW1000](https://www.foshk.com/Wifi_Weather_Station/GW1000.html)
distributed by [Froggit](https://www.froggit.de/product_info.php?info=p410_dp1500-pro-wi-fi-wetterserver-usb-dongle.html)
but will probably also work with similar systems like the [WH26XX](https://www.foshk.com/cables/WH2600.html)
and [GW2000](https://www.foshk.com/Wifi_Weather_Station/GW2001.html).
