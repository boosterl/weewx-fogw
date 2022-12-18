#!/usr/bin/python
#
# Copyright 2022 Bram Oosterlynck
#
# weewx driver that reads data from a Fine Offset WiFi gateway
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.
#
# See http://www.gnu.org/licenses/


# [Station]
#     station_type = FoGW
# [FoGW]
#     poll_interval = 30          # number of seconds
#     gateway_host = 192.168.0.2     # hostname/IP address of the gateway
#     driver = user.fogw

from __future__ import with_statement
import logging
import requests
import time

import weewx.drivers

DRIVER_NAME = 'FoGW'
DRIVER_VERSION = "0.1"

log = logging.getLogger(__name__)

def loader(config_dict, engine):
    return FoGWDriver(**config_dict[DRIVER_NAME])

class FoGWDriver(weewx.drivers.AbstractDevice):
    """weewx driver that reads data from fine offset gateways"""

    OBSERVATION_MAP = {
        "0x02": "outTemp",
        "0x07": "outHumidity",
        "0x03": "dewpoint",
        "0x04": "windchill",
        "0x05": "heatindex",
        "0x0A": "windDir",
        "0x0B": "windSpeed",
        "0x0C": "windGust",
        "0x15": "radiation",
        "0x16": "UV",
        "0x17": "UV",
        "0x10": "rain_total",
    }

    WH25_MAP = {
        "intemp": "inTemp",
        "inhumi": "inHumidity",
        "abs": "pressure",
    }

    WIND_MEASUREMENTS = ["0x0B", "0x0C"]

    def __init__(self, **stn_dict):
        # where to find the gateway
        self.gateway_host = stn_dict.get('gateway_host', '192.168.0.2')
        # how often to poll the gateway, seconds
        self.poll_interval = float(stn_dict.get('poll_interval', 30))
        self._last_rain = None

        log.info("Gateway is %s" % self.gateway_host)
        log.info("Polling interval is %s" % self.poll_interval)

    def genLoopPackets(self):
        while True:

            # map the data into a weewx loop packet
            _packet = {'dateTime': int(time.time() + 0.5),
                       'usUnits': weewx.METRICWX}

            weather_data = requests.get(f"http://{self.gateway_host}/get_livedata_info").json()
            for observation in weather_data["common_list"]:
                if observation["id"] in self.OBSERVATION_MAP and observation["id"] in self.WIND_MEASUREMENTS:
                    _packet[self.OBSERVATION_MAP.get(observation["id"])] = self.format_value(observation["val"]) / 3.6
                elif observation["id"] in self.OBSERVATION_MAP:
                    _packet[self.OBSERVATION_MAP.get(observation["id"])] = self.format_value(observation["val"])
            for observation in weather_data["rain"]:
                if observation["id"] in self.OBSERVATION_MAP:
                    if self.OBSERVATION_MAP.get(observation["id"]) == 'rain_total':
                        newtot = self.format_value(observation["val"])
                        _packet['rain'] = self._delta_rain(newtot, self._last_rain)
                        self._last_rain = new_tot
            for wh25_values in weather_data["wh25"]:
                for wh25_id, wh25_value in wh25_values.items():
                    if wh25_id in self.WH25_MAP:
                        _packet[self.WH25_MAP.get(wh25_id)] = self.format_value(wh25_value)
            yield _packet
            time.sleep(self.poll_interval)

    def format_value(self, raw_value):
        return float(raw_value.split()[0].replace("%", ""))

    def _delta_rain(self, rain, last_rain):
        if last_rain is None:
            log.inf("skipping rain measurement of %s: no last rain" % rain)
            return None
        if rain < last_rain:
            log.inf("rain counter wraparound detected: new=%s last=%s" %
                   (rain, last_rain))
            return rain
        return rain - last_rain

    @property
    def hardware_name(self):
        return "FoGW"

# To test this driver, run it directly as follows:
#   PYTHONPATH=/home/weewx/bin python /home/weewx/bin/user/fogw.py
if __name__ == "__main__":
    import weeutil.weeutil
    import weeutil.logger
    import weewx
    weewx.debug = 1
    weeutil.logger.setup('fogw', {})

    driver = FoGWDriver()
    for packet in driver.genLoopPackets():
        print(weeutil.weeutil.timestamp_to_string(packet['dateTime']), packet)
