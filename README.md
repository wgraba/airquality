# AirQuality
Get stats from nearest airnow.gov monitors and optionally push into InfluxDB.

## Why?
The AirNow website and mobiles apps work well, but I wanted data on monitors
closest to my location rather than a ["reporting area"](https://docs.airnowapi.org/faq#reportingAreaData)
that I could publish to a dashboard for quick viewing.

## Requirements
* Python 3.6+
* Requirements described in `requirements.txt`
* Docker and Docker Compose (if using)
* Account with [AirNow API](https://docs.airnowapi.org/) (free)
* Pretty much US only, but could be extended to other areas where AirNow monitors are 
  available

## Usage
### Without Docker
* Create virtual environment - `python -m venv venv` (not necessary, but recommended)
* Install Python requirements - `pip install -r requirements.txt`
* Run `python ./get-aq.py --help` for usage

### With Docker Compose
* Install Docker and Docker Compose
* Create environment file `.env`; use `example_env` as template
* Adjust `docker-compose.yml` as needed
* Run `docker-compose up -d`

## Development
* Install Python requirements - `pip install -r requirements.txt`
* `black` is used for code formatting

The intent of the design is pretty simple -
* Get location of interest (origin)
* Calculate bounding box around origin and find monitors within bounding box from
  AirNow
* Find closest monitors for each pollutant type
* Optionally push into InfluxDB

## TODO
- [x] Get closest monitors for each pollutant type and output to console
- [x] Implement push of monitor data to Influxdb
- [x] Add example `Dockerfile`
- [x] Add example `docker-compose.yml`
- [x] Add example environment file for docker-compose
- [ ] Handle TLS instead of ignoring for InfluxDB connection
- [ ] Option to enter long., lat. for origin instead of postal code
  - [x] CLI
  - [ ] Docker
- [ ] Consider monitor distance and loc. coords. as InfluxDB Fields instead of Tags
- [ ] Is there a better way to handle cords. vs postal code on CLI
