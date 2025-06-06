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
import weewx.units

DRIVER_NAME = 'FoGW'
DRIVER_VERSION = "0.1"

log = logging.getLogger(__name__)

def loader(config_dict, engine):
    return FoGWDriver(**config_dict[DRIVER_NAME])

class FoGWDriver(weewx.drivers.AbstractDevice):
    """weewx driver that reads data from fine offset gateways"""

    BATTERY_MAP = {
        "0": 0,
        "1": 1,
        "2": 0,
        "3": 0,
        "4": 0,
        "5": 0,
        "6": 0,
    }

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
        "0x0E": "rainRate",
        "0x10": "rain_total",
    }

    CONVERSION_MAP_TEMP = {
        "0": "degree_C",
        "1": "degree_F",
    }

    CONVERSION_MAP_WIND = {
        "0": "meter_per_second",
        "1": "km_per_hour",
        "2": "mile_per_hour",
        "3": "knot",
    }

    CONVERSION_MAP_PRESSURE = {
        "0": "hPa",
        "1": "inHg",
        "2": "mmHg",
    }

    CONVERSION_MAP_RAIN = {
        "0": "mm",
        "1": "inch",
    }

    CONVERSION_MAP_RAIN_RATE = {
        "0": "mm_per_hour",
        "1": "inch_per_hour",
    }

    CONVERSION_MAP_IRRADIANCE = {
        "1": "watt_per_meter_squared",
    }

    TEMPERATURE_IDS = ["0x02", "0x03", "0x04", "0x05", "intemp"]

    WIND_IDS = ["0x0B", "0x0C"]

    PRESSURE_IDS = ["abs"]

    RAIN_IDS = ["0x10"]

    RAIN_RATE_IDS = ["0x0E"]

    IRRADIANCE_IDS = ["0x15"]

    CONVERSION_MAP = [
        {
            "observation_type": "temperature",
            "observation_alias": "temperature",
            "ids": TEMPERATURE_IDS,
            "conversion_map": CONVERSION_MAP_TEMP,
        },
        {
            "observation_type": "wind",
            "observation_alias": "wind",
            "ids": WIND_IDS,
            "conversion_map": CONVERSION_MAP_WIND,
        },
        {
            "observation_type": "pressure",
            "observation_alias": "pressure",
            "ids": PRESSURE_IDS,
            "conversion_map": CONVERSION_MAP_PRESSURE,
        },
        {
            "observation_type": "rain",
            "observation_alias": "rain",
            "ids": RAIN_IDS,
            "conversion_map": CONVERSION_MAP_RAIN,
        },
        {
            "observation_type": "rain",
            "observation_alias": "rain_rate",
            "ids": RAIN_RATE_IDS,
            "conversion_map": CONVERSION_MAP_RAIN_RATE,
        },
        {
            "observation_type": "light",
            "observation_alias": "light",
            "ids": IRRADIANCE_IDS,
            "conversion_map": CONVERSION_MAP_IRRADIANCE,
        },
    ]

    SIGNAL_STRENGTH_MAP = {
        "0": 0,
        "1": 25,
        "2": 50,
        "3": 75,
        "4": 100,
    }

    UNIT_MAP_DESTINATION = {
        "0x02": "degree_C",
        "0x03": "degree_C",
        "0x04": "degree_C",
        "0x05": "degree_C",
        "intemp": "degree_C",
        "0x0B": "meter_per_second",
        "0x0C": "meter_per_second",
        "abs": "mbar",
        "0x10": "mm",
        "0x0E": "mm_per_hour",
        "0x15": "watt_per_meter_squared",
    }

    UNIT_MAP_SOURCE = {
        "0x02": ["degree_C", "group_temperature"],
        "0x03": ["degree_C", "group_temperature"],
        "0x04": ["degree_C", "group_temperature"],
        "0x05": ["degree_C", "group_temperature"],
        "intemp": ["degree_C", "group_temperature"],
        "0x0B": ["meter_per_second", "group_speed"],
        "0x0C": ["meter_per_second", "group_speed"],
        "abs": ["mbar", "group_pressure"],
        "0x10": ["mm", "group_rain"],
        "0x0E": ["mm_per_hour", "group_rainrate"],
        "0x15": ["watt_per_meter_squared", "group_radiation"],
        "distance": ["km", "group_distance"],
    }

    WH25_MAP = {
        "intemp": "inTemp",
        "inhumi": "inHumidity",
        "abs": "pressure",
    }

    LIGHTNING_MAP = {
        "distance": "lightning_distance",
        "count": "lightning_strike_count",
    }

    CH_AISLE_MAP = {
        "temp": "outTemp",
        "humidity": "outHumidity",
    }

    def __init__(self, **stn_dict):
        # where to find the gateway
        self.gateway_host = stn_dict.get('gateway_host', '192.168.0.2')
        # how often to poll the gateway, seconds
        self.poll_interval = float(stn_dict.get('poll_interval', 30))
        self._last_rain = None
        self._last_strikes = None

        log.info("Gateway is %s" % self.gateway_host)
        log.info("Polling interval is %s" % self.poll_interval)

    def genLoopPackets(self):
        while True:
            # Map units everytime in case the units have been changed
            self.map_units()

            # map the data into a weewx loop packet
            _packet = {'dateTime': int(time.time() + 0.5),
                       'usUnits': weewx.METRICWX}

            try:
                weather_data = requests.get(f"http://{self.gateway_host}/get_livedata_info").json()
                for observation in weather_data.get("common_list", list()):
                    if observation["id"] in self.OBSERVATION_MAP:
                        _packet[self.OBSERVATION_MAP.get(observation["id"])] = self.convert_value(
                            observation["id"],
                            self.format_value(observation["val"]))
                for observation in weather_data.get("rain", list()):
                    if observation["id"] in self.OBSERVATION_MAP:
                        if self.OBSERVATION_MAP.get(observation["id"]) == 'rain_total':
                            newtot = self.convert_value(observation["id"], self.format_value(observation["val"]))
                            _packet['rain'] = self._delta_rain(newtot, self._last_rain)
                            self._last_rain = newtot
                        else:
                            _packet[self.OBSERVATION_MAP.get(observation["id"])] = self.convert_value(
                                observation["id"],
                                self.format_value(observation["val"]))
                for wh25_values in weather_data.get("wh25", list()):
                    for wh25_id, wh25_value in wh25_values.items():
                        if wh25_id in self.WH25_MAP:
                            _packet[self.WH25_MAP.get(wh25_id)] = self.convert_value(wh25_id, self.format_value(wh25_value))
                for lightning_values in weather_data.get("lightning", list()):
                    lightning_strike_count = lightning_values.get("count")
                    lightning_distance = lightning_values.get("distance")
                    newtot = self.format_value(lightning_strike_count)
                    delta_value = self._delta_strikes(newtot, self._last_strikes)
                    _packet[self.LIGHTNING_MAP.get("count")] = delta_value
                    self._last_strikes = newtot
                    if delta_value and lightning_distance != "--.-":
                        _packet[self.LIGHTNING_MAP.get("distance")] = self.convert_value("distance", self.format_value(lightning_distance))
                for ch_aisle_values in weather_data.get("ch_aisle", list()):
                    for ch_aisle_id, ch_aisle_value in ch_aisle_values.items():
                        if ch_aisle_id in self.CH_AISLE_MAP:
                            _packet[self.CH_AISLE_MAP.get(ch_aisle_id)] = self.convert_value(ch_aisle_id, self.format_value(ch_aisle_value))
                for status_type, status_value in self.check_sensor_status().items():
                    _packet[status_type] = status_value
            except requests.exceptions.RequestException as e:
                log.error("Error executing request to gateway %s" % e)
            yield _packet
            time.sleep(self.poll_interval)

    def check_sensor_status(self):
        sensor_status = dict()
        try:
            sensors1 = requests.get(f"http://{self.gateway_host}/get_sensors_info?page=1").json()
            sensors2 = requests.get(f"http://{self.gateway_host}/get_sensors_info?page=2").json()
            for sensor in sensors1 + sensors2:
                if sensor["id"] != "FFFFFFFF" and sensor["id"] != "FFFFFFFE":
                    sensor_status["rxCheckPercent"] = self.SIGNAL_STRENGTH_MAP[sensor["signal"]]
                    sensor_status["txBatteryStatus"] = self.BATTERY_MAP[sensor["batt"]]
                    break
        except requests.exceptions.RequestException as e:
            log.error("Error executing request to gateway %s" % e)
        return sensor_status

    def convert_value(self, observation_id, observation_value):
        if observation_id in self.UNIT_MAP_SOURCE and observation_id in self.UNIT_MAP_DESTINATION:
            return weewx.units.convert(
                (observation_value, self.UNIT_MAP_SOURCE[observation_id][0], self.UNIT_MAP_SOURCE[observation_id][0]),
                self.UNIT_MAP_DESTINATION[observation_id]
            )[0]
        return observation_value

    def format_value(self, raw_value):
        return float(raw_value.split()[0].replace("%", ""))

    def map_units(self):
        try:
            unit_info = requests.get(f"http://{self.gateway_host}/get_units_info").json()
            for conversion in self.CONVERSION_MAP:
                for observation_id in conversion["ids"]:
                    if configured_unit := conversion["conversion_map"].get(unit_info[conversion["observation_type"]]):
                        if self.UNIT_MAP_SOURCE[observation_id][0] != configured_unit:
                            log.info("Units for %s will be converted from %s to %s" %
                            (
                                conversion["observation_type"],
                                configured_unit,
                                self.UNIT_MAP_DESTINATION[observation_id]
                            ))
                            self.UNIT_MAP_SOURCE[observation_id][0] = configured_unit
                            self._last_rain = None
                    else:
                        log.error("Unit for %s is not known, bogus values may appear" % conversion["observation_alias"])
        except requests.exceptions.RequestException as e:
            log.error("Error executing request to gateway %s" % e)

    @staticmethod
    def _delta_rain(rain, last_rain):
        if last_rain is None:
            log.info("skipping rain measurement of %s: no last rain" % rain)
            return None
        if rain < last_rain:
            log.info("rain counter wraparound detected: new=%s last=%s" %
                   (rain, last_rain))
            return rain
        return rain - last_rain

    @staticmethod
    def _delta_strikes(strikes, last_strikes):
        if strikes is None:
            return None
        if last_strikes is None:
            log.info("skipping lightning strikes measurement of %s: no last strikes" % strikes)
            return None
        if strikes < last_strikes:
            log.info("lightning strikes wraparound detected: new=%s last=%s" %
                   (strikes, last_strikes))
            return strikes
        return strikes - last_strikes

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
