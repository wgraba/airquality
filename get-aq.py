#!/usr/bin/env python3


import argparse
import enum
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


class SimpleGeocoder:
    def __init__(self) -> None:
        self._geocoder = geopy.geocoders.Nominatim(user_agent="covid-appointments")

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
    type: MonitorType
    loc: geopy.Point
    aqi: int
    conc: int
    conc_units: ConcUnits


def get_monitors(
    loc: geopy.Point,
    dist_mi: float,
) -> Union[List[Monitor], None]:
    min_point = geopy.distance.distance(miles=dist_mi).destination(loc, bearing=225)
    max_point = geopy.distance.distance(miles=dist_mi).destination(loc, bearing=45)

    return None


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

    # sess = requests.Session()

    logger.info(
        f"Looking for monitors within {cli_args.distance}mi of {cli_args.postalcode}"
    )
