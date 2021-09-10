#!/usr/bin/env python3


import argparse
import datetime
import enum
from json.decoder import JSONDecodeError
import geopy
import geopy.geocoders
import geopy.distance
import logging
import requests
from typing import List, NamedTuple, Union
import logging
from rich import print
from rich.logging import RichHandler
from rich.traceback import install

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
    OZONE = enum.auto()
    PM2p5 = enum.auto()
    PM10 = enum.auto()


class ConcUnits(enum.Enum):
    UG_M3 = enum.auto()
    PPB = enum.auto()


class Monitor(NamedTuple):
    name: str
    type: MonitorType
    loc: geopy.Point
    aqi: int
    conc: float
    raw_conc: float
    conc_units: ConcUnits


def get_monitors(
    loc: geopy.Point,
    dist_mi: float,
    session: requests.Session,
) -> Union[List[Monitor], List[None]]:
    """
    Get nearest monitors for O3, PM2.5, and PM10

    A bounding box as required by the airnow.gov API is calculated from `loc`
    and `dist_mi`.

    +-------------------------+
    |                         |
    |                         |
    |            *            |
    |                         |
    |                         |
    +-------------------------+

    :param loc: Location to search from
    :param dist_mi: Distance in miles to search from loc
    :param session: Request session with API key defaulted
    :return: List of Monitors
    """
    monitors = []
    min_point = geopy.distance.distance(miles=dist_mi).destination(loc, bearing=225)
    max_point = geopy.distance.distance(miles=dist_mi).destination(loc, bearing=45)

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
            # Parse Monitor Type
            mon_type = None
            if raw_mon["Parameter"] == "OZONE":
                mon_type = MonitorType.OZONE

            elif raw_mon["Parameter"] == "PM2.5":
                mon_type = MonitorType.PM2p5

            elif raw_mon["Parameter"] == "PM10":
                mon_type = MonitorType.PM10

            if not mon_type:
                raise ValueError(f"Unknown Monitor Type {raw_mon['Parameter']}")

            # Parse Concentration Units
            conc_units = None
            if raw_mon["Unit"] == "UG/M3":
                conc_units = ConcUnits.UG_M3

            elif raw_mon["Unit"] == "PPB":
                conc_units = ConcUnits.PPB

            if not conc_units:
                raise ValueError(f"Unkown Concentation Units {raw_mon['Unit']}")

            monitor = Monitor(
                name=raw_mon["SiteName"],
                type=mon_type,
                loc=geopy.Point(raw_mon["Latitude"], raw_mon["Longitude"]),
                aqi=raw_mon["AQI"],
                conc=raw_mon["Value"],
                raw_conc=raw_mon["RawConcentration"],
                conc_units=conc_units,
            )
            monitors.append(monitor)

    return monitors


if __name__ == "__main__":
    cli_parser = argparse.ArgumentParser(
        description="Get closest monitors for O3, PM2.5, and PM10.0 and optionally put into InfluxDB"
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
    cli_parser.add_argument("-t", "--token", help="InfluxDB Token")
    cli_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose output"
    )

    cli_args = cli_parser.parse_args()

    if cli_args.verbose:
        logger.setLevel(logging.INFO)

    logger.info(
        f"Looking for monitors within {cli_args.distance}mi of {cli_args.postalcode}"
    )

    sess = requests.Session()
    sess.params = {"api_key": cli_args.api_key}

    geocoder = SimpleGeocoder()
    loc = geocoder.get_loc(cli_args.postalcode)

    monitors = get_monitors(loc, cli_args.distance, sess)

    print(monitors)
