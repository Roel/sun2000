# Sun2000: Huawei SUN2000 inverter data reader
# Copyright (C) 2023-2024  Roel Huybrechts

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import asyncio
import datetime
import time
import os

from huawei_solar import AsyncHuaweiSolar
from influxdb import InfluxDBClient

INFLUX_HOST = os.environ['INFLUX_HOST']
INFLUX_DB = os.environ['INFLUX_DB']
INFLUX_USER = os.environ['INFLUX_USER']
INFLUX_PASS = os.environ['INFLUX_PASS']

SUN2000_HOST = os.environ['SUN2000_HOST']
SUN2000_PORT = int(os.environ['SUN2000_PORT'])

dbclient = InfluxDBClient(INFLUX_HOST, database=INFLUX_DB,
                          username=INFLUX_USER, password=INFLUX_PASS)


async def get_solar_data():
    conn = await AsyncHuaweiSolar.create(SUN2000_HOST, port=SUN2000_PORT)

    registers = [
        'active_power',
        'daily_yield_energy',
        'accumulated_yield_energy',
        'internal_temperature',
        'grid_voltage',
        'pv_01_voltage',
        'pv_01_current',
        'pv_02_voltage',
        'pv_02_current'
    ]

    while True:
        data = []

        for r in registers:
            ms = {}
            ms["time"] = int(datetime.datetime.now().strftime('%s')) * 10**9
            result = await conn.get(r)

            ms["measurement"] = r
            ms["fields"] = {"value": result.value}
            ms['tags'] = {"unit": result.unit}
            if result.value > 0:
                data.append(ms)

        dbclient.write_points(data)
        time.sleep(30)

asyncio.run(get_solar_data())
