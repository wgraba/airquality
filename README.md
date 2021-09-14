# AirQuality
Get stats from nearest airnow.gov monitors and push into InfluxDB.

## Requirements
* Python 3.6+

## Usage
### Without Docker
* Install Python requirements - `pip install -r requirements.txt`
* Run `python ./get-aq.py --help`

### With Docker Compose
* Install Docker and Docker Compose
* Create environment file `.env`; use `example_env` as template
* Run `docker-compose up -d`

## Development
* Install Python requirements - `pip install -r requirements.txt`
* `black` is used for code formatting

## TODO
- [x] Get closest monitors for each pollutant type and output to console
- [x] Implement push of monitor data to Influxdb
- [x] Add example `Dockerfile`
- [x] Add example `docker-compose.yml`
- [x] Add example environment file for docker-compose
- [ ] Handle TLS instead of ignoring for InfluxDB connection
- [ ] Poll airnow.gov at top of hour since that is when sensos are updated