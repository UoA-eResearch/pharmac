# pharmac

[![Update CSVs](https://github.com/UoA-eResearch/pharmac/actions/workflows/fetch.yml/badge.svg)](https://github.com/UoA-eResearch/pharmac/actions/workflows/fetch.yml)

Python script to extract priority lists for funding applications from the Pharmac website (https://connect.pharmac.govt.nz/apptracker/s/ranking-lists-for-funding-applications?reportType=OFI) and monitor for changes

### Installation 

`pip install -r requirements.txt`

### Running

`./fetch.py`

This runs every 5 minutes via a GitHub action, which commits here

### Copyright

The data collected by this project originates from [pharmac.govt.nz](https://www.pharmac.govt.nz/) and is owned by Pharmac. It is licensed under the [Creative Commons Attribution 4.0 International (CC-BY 4.0) licence](https://creativecommons.org/licenses/by/4.0/). Pharmac does not endorse this project or its use of the content. See [Pharmac's copyright statement](https://www.pharmac.govt.nz/about-this-site/copyright) for further details.
