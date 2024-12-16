# pharmac

[![Update CSV](https://github.com/UoA-eResearch/pharmac/actions/workflows/fetch.yml/badge.svg)](https://github.com/UoA-eResearch/pharmac/actions/workflows/fetch.yml)

Python script to extract priority lists for funding applications from the Pharmac website (https://connect.pharmac.govt.nz/apptracker/s/ranking-lists-for-funding-applications?reportType=OFI) and monitor for changes

### Installation 

`pip install -r requirements.txt`

### Running

`./fetch.py`

This runs every 5 minutes via a GitHub action, which commits here
