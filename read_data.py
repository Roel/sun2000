# Sun2000: Huawei SUN2000 inverter data reader
# Copyright (C) 2023-2026  Roel Huybrechts, KanteTaete

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
import sys
import atexit

from huawei_solar import AsyncHuaweiSolar

# Lib for InfluxDB v1
from influxdb import InfluxDBClient
# Lib for InfluxDB v2
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS


def read_secret(variable_name):
    if f'{variable_name}_FILE' in os.environ:
        with open(os.environ.get(f'{variable_name}_FILE'), 'r') as secret_file:
            secret = secret_file.read()
    else:
        secret = os.environ.get(variable_name, None)
    return secret

INFLUX_DB_VERSION = int(os.environ['INFLUX_DB_VERSION'])

# Variables for InfluxDB version v1
INFLUX_V1_HOST = os.environ['INFLUX_V1_HOST']
INFLUX_V1_DB = os.environ['INFLUX_V1_DB']
INFLUX_V1_USERNAME = os.environ['INFLUX_V1_USERNAME']
INFLUX_V1_PASSWORD = read_secret('INFLUX_V1_PASSWORD')

# Variables for InfluxDB version v2
INFLUX_V2_URL = os.environ['INFLUX_V2_URL']
INFLUX_V2_BUCKET = os.environ['INFLUX_V2_BUCKET']
INFLUX_V2_ORG = os.environ['INFLUX_V2_ORG']
INFLUX_V2_TOKEN = os.environ['INFLUX_V2_TOKEN']


SUN2000_HOST = os.environ['SUN2000_HOST']
SUN2000_PORT = int(os.environ['SUN2000_PORT'])
SUN2000_SLAVE_ID = int(os.environ.get('SUN2000_SLAVE_ID'))
SUN2000_TIMEOUT = int(os.environ.get('SUN2000_TIMEOUT'))


READ_INTERVAL = int(os.environ.get('READ_INTERVAL'))

def on_exit(db_client: influxdb_client.InfluxDBClient, write_api: influxdb_client.InfluxDBClient.write_api):
    """Close clients after terminate a script.

    :param db_client: InfluxDB client
    :param write_api: WriteApi
    :return: nothing
    """
    write_api.close()
    db_client.close()


if INFLUX_DB_VERSION == 1:
    dbclient = InfluxDBClient(INFLUX_V1_HOST, database=INFLUX_V1_DB,
                          username=INFLUX_V1_USERNAME, password=INFLUX_V1_PASSWORD)
elif INFLUX_DB_VERSION == 2:
    dbclient = influxdb_client.InfluxDBClient(url=INFLUX_V2_URL, token=INFLUX_V2_TOKEN,org=INFLUX_V2_ORG)
    write_api=dbclient.write_api(write_options=SYNCHRONOUS)
else:
    sys.stderr.write('Error: No InfluxDB version given in environement variable "INFLUX_DB_VERSION" (file "environment.env").')
    exit(1)


async def get_solar_data():
    conn = await AsyncHuaweiSolar.create(host=SUN2000_HOST, port=SUN2000_PORT, slave_id=SUN2000_SLAVE_ID, timeout=SUN2000_TIMEOUT)
    sys.stdout.write(f'Connected to Huawei SUN2000 inverter, host: {SUN2000_HOST}:{SUN2000_PORT} (slave ID: {SUN2000_SLAVE_ID})\n')

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
    # sleep 2 seconds to ensure connection is established
    time.sleep(2)

    while True:
        data = []

        for r in registers:
            ms = {}
            ms["time"] = int(datetime.datetime.now().strftime('%s')) * 10**9
            result = await conn.get(name=r,slave_id=SUN2000_SLAVE_ID)

            ms["measurement"] = r
            ms["fields"] = {"value": result.value}
            ms["tags"] = {"unit": result.unit}
            sys.stdout.write(f'Read register "{r}": {result.value} {result.unit}\n')
            if result.value > 0:
                data.append(ms)

        if INFLUX_DB_VERSION == 1:
            dbclient.write_points(data)
        elif INFLUX_DB_VERSION == 2:
            write_api.write(bucket=INFLUX_V2_BUCKET, org=INFLUX_V2_ORG, record=data)

        sys.stdout.write(f'Going to sleep for {READ_INTERVAL} seconds.\n')
        time.sleep(READ_INTERVAL)

    # close connection to inverter
    await conn.stop()
    sys.stdout.write('Connection to Huawei SUN2000 inverter closed.\n')

asyncio.run(get_solar_data())


"""
Call after terminate a script
"""
atexit.register(on_exit, dbclient, write_api)