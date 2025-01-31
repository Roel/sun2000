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


def read_secret(variable_name):
    if f'{variable_name}_FILE' in os.environ:
        with open(os.environ.get(f'{variable_name}_FILE'), 'r') as secret_file:
            secret = secret_file.read()
    else:
        secret = os.environ.get(variable_name, None)
    return secret


INFLUX_HOST = os.environ['INFLUX_HOST']
INFLUX_DB = os.environ['INFLUX_DB']
INFLUX_USERNAME = os.environ['INFLUX_USERNAME']
INFLUX_PASSWORD = read_secret('INFLUX_PASSWORD')

SUN2000_HOST = os.environ['SUN2000_HOST']
SUN2000_PORT = int(os.environ['SUN2000_PORT'])

READ_INTERVAL = int(os.environ.get('READ_INTERVAL', 30))

dbclient = InfluxDBClient(INFLUX_HOST, database=INFLUX_DB,
                          username=INFLUX_USERNAME, password=INFLUX_PASSWORD)


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
        time.sleep(READ_INTERVAL)

asyncio.run(get_solar_data())
