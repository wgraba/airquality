#!/usr/bin/env python3


import argparse
import datetime
import enum
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
from json.decoder import JSONDecodeError
import geopy
import geopy.geocoders
import geopy.distance
import logging
import requests
from typing import Dict, List, NamedTuple, Union
import logging
from rich import print
from rich.logging import RichHandler
from rich.table import Table
from rich.traceback import install
import time

install(show_locals=True)

logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)


logger = logging.getLogger(__name__)


AIRNOW_API_URL = "https://www.airnowapi.org/aq/"
AIRNOW_API_DATA_QUERY_URL = AIRNOW_API_URL + "data/"
POLL_TIME_SLEEP_S = 30 * 60  # Sleep for 30 min. since data at airnow.gov is
# updated 1/hr


class SimpleGeocoder:
    def __init__(self) -> None:
        self._geocoder = geopy.geocoders.Nominatim(user_agent="get-aq")

    def get_loc(self, postalcode: int) -> geopy.Point:
        """
        Get location by Postal Code

        :param postalcode: Postal Code
        :return: Tuple representing (latitidue, longitude) or None if location not found
        """
        loc = self._geocoder.geocode({"postalcode": postalcode}, country_codes="us")
        if not isinstance(loc, geopy.Location):
            raise ValueError(f"No location found for postal code {postalcode}")

        return geopy.Point(latitude=loc.latitude, longitude=loc.longitude)


class MonitorType(enum.Enum):
    OZONE = "OZONE"
    PM2p5 = "PM2.5"
    PM10 = "PM10"

    def __str__(self) -> str:
        return self.value


class ConcUnits(enum.Enum):
    UG_M3 = "UG/M3"
    PPB = "PPB"

    def __str__(self) -> str:
        return self.value


class Monitor(NamedTuple):
    name: str
    time: datetime.datetime
    type: MonitorType
    loc: geopy.Point
    distance_mi: float
    aqi: int
    conc: float
    raw_conc: float
    conc_units: ConcUnits


def get_monitors(
    origin_loc: geopy.Point,
    dist_mi: float,
    session: requests.Session,
) -> Union[List[Monitor], None]:
    """
    Get monitors for O3, PM2.5, and PM10

    A bounding box as required by the airnow.gov API is calculated from `loc`
    and `dist_mi`.

    +-------------------------+
    |                         |
    |                         |
    |            *            |
    |                         |
    |                         |
    +-------------------------+

    :param origin_loc: Location to search from
    :param dist_mi: Distance in miles to search from loc
    :param session: Request session with API key defaulted
    :return: List of Monitors or None if no monitors found
    """
    monitors = []
    min_point = geopy.distance.distance(miles=dist_mi).destination(
        origin_loc, bearing=225
    )
    max_point = geopy.distance.distance(miles=dist_mi).destination(
        origin_loc, bearing=45
    )

    # https://www.airnowapi.org/aq/data/?startDate=2021-09-10T22&endDate=2021-09-10T23&parameters=OZONE,PM25,PM10&BBOX=-106.171227,39.144701,-103.556480,40.427867&dataType=B&format=application/json&verbose=0&monitorType=0&includerawconcentrations=0&API_KEY=20089F4D-6621-46B0-9046-98860751C5E9
    rsp = session.get(
        AIRNOW_API_DATA_QUERY_URL,
        params={
            "parameters": "OZONE,PM25,PM10",  # O3, PM2.5, PM10.0
            "bbox": f"{min_point.longitude},{min_point.latitude},{max_point.longitude},{max_point.latitude}",
            "monitortype": 0,  # Permanent monitors only
            "datatype": "B",  # Concentrations & AQI
            "format": "application/json",
            "verbose": 1,
            "includerawconcentrations": 1,
        },
    )
    raw_monitors = None
    try:
        rsp.raise_for_status()
        raw_monitors = rsp.json()

    except (requests.HTTPError, JSONDecodeError) as err:
        logger.error(f"Error in response: {err}")

    if raw_monitors:
        for raw_mon in raw_monitors:
            mon_loc = geopy.Point(raw_mon["Latitude"], raw_mon["Longitude"])
            monitor = Monitor(
                name=raw_mon["SiteName"],
                time=datetime.datetime.fromisoformat(raw_mon["UTC"]),
                type=MonitorType(raw_mon["Parameter"]),
                loc=mon_loc,
                distance_mi=geopy.distance.distance(origin_loc, mon_loc).mi,
                aqi=raw_mon["AQI"],
                conc=raw_mon["Value"],
                raw_conc=raw_mon["RawConcentration"],
                conc_units=ConcUnits(raw_mon["Unit"]),
            )
            monitors.append(monitor)

            logger.debug(monitor)

    return monitors if len(monitors) > 0 else None


def get_closest_monitors(monitors: List[Monitor]) -> Dict:
    """
    Get closest monitors for each pollutant type

    :param monitors: List of nearby monitors to search through
    :return: Dictionary by pollutant type of closest monitors
    """
    # closest_mons = {
    #     MonitorType.OZONE: None,
    #     MonitorType.PM2p5: None,
    #     MonitorType.PM10: None,
    # }
    closest_mons = {}

    for monitor in monitors:
        if monitor.type not in closest_mons or abs(monitor.distance_mi) < abs(
            closest_mons[monitor.type].distance_mi
        ):
            closest_mons[monitor.type] = monitor

    return closest_mons


def write_influxdb(client: InfluxDBClient, bucket: str, monitor: Monitor):
    """
    Write monitors to Influxdb

    :param client: InfluxDB client
    :param bucket: Bucket to write to
    :param monitors: Dictionary of monitors by pollutant type to write to
                     database
    """
    write_api = client.write_api(write_options=SYNCHRONOUS)

    logger.debug(f"Writing {monitor} to {bucket} in {client.org}@{client.url}")

    point = {
        "time": monitor.time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "measurement": monitor.type,
        "tags": {
            "name": monitor.name,
            "longitude": monitor.loc.longitude,
            "latitude": monitor.loc.latitude,
            "distance": monitor.distance_mi,
            "units": monitor.conc_units,
        },
        "fields": {
            "AQI": monitor.aqi,
            "Concentration": monitor.conc,
            "Raw Concentration": monitor.raw_conc,
        },
    }
    write_api.write(bucket=bucket, record=point)


if __name__ == "__main__":
    cli_parser = argparse.ArgumentParser(
        description="Get closest monitors for pollutants and optionally put into InfluxDB"
    )
    cli_parser.add_argument(
        "postalcode", type=int, help="Postal code to use for search"
    )
    cli_parser.add_argument(
        "distance", type=float, help="Distance in miles from postalcode to search"
    )
    cli_parser.add_argument("api_key", type=str, help="airnow.gov API key")

    cli_parser.add_argument("-b", "--bucket", help="InfluxDB Bucket")
    cli_parser.add_argument("-o", "--org", help="InfluxDB Organization")
    cli_parser.add_argument(
        "-s",
        "--sleep",
        type=float,
        default=POLL_TIME_SLEEP_S,
        help=f"Time to sleep between airnow.gov reads; default {POLL_TIME_SLEEP_S}s",
    )
    cli_parser.add_argument("-t", "--token", help="InfluxDB Token")
    cli_parser.add_argument("-u", "--url", help="InfluxDB URL")
    cli_parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Verbose output; can be used multiple times to increase verbosity",
    )

    cli_args = cli_parser.parse_args()

    if cli_args.verbose > 0:
        if cli_args.verbose > 1:
            logger.setLevel(logging.DEBUG)

        else:
            logger.setLevel(logging.INFO)

    logger.info(
        f"Looking for monitors within {cli_args.distance}mi of {cli_args.postalcode}"
    )

    sess = requests.Session()
    sess.params = {"api_key": cli_args.api_key}

    geocoder = SimpleGeocoder()
    loc = geocoder.get_loc(cli_args.postalcode)

    if cli_args.url and cli_args.token and cli_args.org and cli_args.bucket:
        influx_client = InfluxDBClient(
            url=cli_args.url, token=cli_args.token, org=cli_args.org, verify_ssl=False
        )

        logger.info(f"InfluxDB: {cli_args.org}@{cli_args.url}")

    else:
        influx_client = None

    while True:
        try:
            monitors = get_monitors(loc, cli_args.distance, sess)
            if monitors:
                monitors = get_closest_monitors(monitors)

                mon_table = Table(title="Closest Monitors")
                mon_table.add_column("Time(UTC)")
                mon_table.add_column("Name")
                mon_table.add_column("Distance(mi)")
                mon_table.add_column("Type")
                mon_table.add_column("AQI")
                mon_table.add_column("Concentration")

                for monitor in monitors.values():
                    mon_table.add_row(
                        str(monitor.time),
                        str(monitor.name),
                        f"{monitor.distance_mi:0.2f}",
                        str(monitor.type),
                        str(monitor.aqi),
                        f"{monitor.conc:0.1f}{monitor.conc_units}",
                    )

                    if influx_client:
                        write_influxdb(influx_client, cli_args.bucket, monitor)

                print(mon_table)

            else:
                logger.error(f"No monitors found!")

            logger.info(f"Sleeping for {cli_args.sleep}s")
            time.sleep(cli_args.sleep)

        except KeyboardInterrupt:
            print("Quitting...")
            break
