# AirQuality
Get stats from nearest airnow.gov sensors and push into influxdb.

## Requirements
* Python 3.6+

## Usage
* Install Python requirements - `pip install -r requirements.txt`

## Development
* Install Python requirements - `pip install -r requirements.txt`
* `black` is used for code formatting

## TODO
- [x] Get closest monitors for each pollutant type and output to console
- [x] Implement push of monitor data to Influxdb
- [ ] Add example `Dockerfile`
- [ ] Add example `docker-compose.yml`
- [ ] Handle TLS besides ignoring for Influxdb connection