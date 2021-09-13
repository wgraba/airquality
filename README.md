# AirQuality
Get stats from nearest airnow.gov monitors and push into InfluxDB.

## Requirements
* Python 3.6+

## Usage
* Install Python requirements - `pip install -r requirements.txt`
* Run `python ./get-aq.py --help`

## Development
* Install Python requirements - `pip install -r requirements.txt`
* `black` is used for code formatting

## TODO
- [x] Get closest monitors for each pollutant type and output to console
- [x] Implement push of monitor data to Influxdb
- [ ] Add example `Dockerfile`
- [ ] Add example `docker-compose.yml`
- [ ] Add example environment file for docker-compose
- [ ] Handle TLS besides ignoring for InfluxDB connection