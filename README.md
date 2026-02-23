# pharmac

[![Update CSVs](https://github.com/UoA-eResearch/pharmac/actions/workflows/fetch.yml/badge.svg)](https://github.com/UoA-eResearch/pharmac/actions/workflows/fetch.yml)

Python script to extract priority lists for funding applications from the Pharmac website (https://connect.pharmac.govt.nz/apptracker/s/ranking-lists-for-funding-applications?reportType=OFI) and monitor for changes

### Installation 

`pip install -r requirements.txt`

### Running

`./fetch.py`

This runs every 5 minutes via a GitHub action, which commits here

### Copyright

The data collected by this project is sourced from the [PHARMAC website](https://www.pharmac.govt.nz/) and is subject to [PHARMAC's copyright](https://www.pharmac.govt.nz/about-this-site/copyright). This project is intended for non-commercial research purposes. Please refer to PHARMAC's copyright statement before reusing any data.
