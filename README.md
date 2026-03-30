# pharmac

[![Update CSVs](https://github.com/UoA-eResearch/pharmac/actions/workflows/fetch.yml/badge.svg)](https://github.com/UoA-eResearch/pharmac/actions/workflows/fetch.yml)

Python script to extract priority lists for funding applications from the Pharmac website (https://connect.pharmac.govt.nz/apptracker/s/ranking-lists-for-funding-applications?reportType=OFI) and monitor for changes

### Installation 

`pip install -r requirements.txt`

### Running

`./fetch.py`

This runs every 5 minutes via a GitHub action, which commits here

---

## FDA / TGA / MedSafe Approval Dates

The `find_approvals.py` script cross-references the Pharmac applications (`Pharmac applications.xlsx`) against drug approval databases from:

- **FDA** (US Food and Drug Administration) – [DrugsFDA data files](https://www.fda.gov/drugs/drug-approvals-and-databases/drugsfda-data-files)
- **TGA** (Australian Therapeutic Goods Administration) – [ARTG Public Summary](https://www.tga.gov.au/resources/artg)
- **MedSafe** (New Zealand Medicines and Medical Devices Safety Authority) – [Product Register Search](https://www.medsafe.govt.nz/DbSearch/)

The script uses fuzzy string matching (via the `thefuzz` library) to match drug names between the Pharmac list and each regulator's database.

### Drug Approval Databases

Pre-built copies of the databases are stored in `data/`:

| Database | Path | Source URL | Retrieved |
|----------|------|------------|-----------|
| FDA DrugsFDA | `data/fda/Products.txt`, `data/fda/Submissions.txt`, `data/fda/Applications.txt` | https://www.fda.gov/media/89850/download | 2026-03-27 |
| MedSafe Register | `data/medsafe/medsafe_register.csv` | https://www.medsafe.govt.nz/DbSearch/ (scraped via wildcard ingredient search) | 2026-03-30 |
| TGA ARTG | `data/tga/tga_artg.csv` | https://www.tga.gov.au/resources/artg | *See note below* |

**TGA Note:** The TGA website (tga.gov.au) may block automated access from cloud/CI environments. To populate the TGA database, download the ARTG Public Summary extract from [tga.gov.au/resources/artg](https://www.tga.gov.au/resources/artg) and save it as `data/tga/tga_artg.csv`. Alternatively, run `python download_databases.py --tga` from your local machine.

### Rebuilding the Databases

To rebuild all databases from scratch:

```bash
pip install -r requirements.txt
python download_databases.py --all
```

Individual databases can be rebuilt with:

```bash
python download_databases.py --fda     # Download FDA DrugsFDA data files
python download_databases.py --tga     # Download TGA ARTG extract
python download_databases.py --medsafe # Scrape MedSafe product register (~30-40 min)
```

**Note:** Building the MedSafe database takes 30–40 minutes because the MedSafe server responds slowly to each query. The database is built by issuing wildcard ingredient searches (a%, b%, ... z%) against the MedSafe product register.

### Running the Approval Date Lookup

```bash
python find_approvals.py
```

Output is saved to `pharmac_approvals.csv`, which contains all columns from `Pharmac applications.xlsx` plus:

| Column | Description |
|--------|-------------|
| `FDA_ApprovalDate` | Earliest FDA approval date for the drug |
| `TGA_ApprovalDate` | Earliest TGA approval date for the drug |
| `MedSafe_ApprovalDate` | Earliest MedSafe approval date for the drug |

Dates are in ISO 8601 format (`YYYY-MM-DD`). Empty values indicate no match was found in that regulator's database.

### Data Provenance

- **FDA data** is in the public domain and available from the US Food and Drug Administration at https://www.fda.gov/drugs/drug-approvals-and-databases/drugsfda-data-files
- **MedSafe data** originates from the New Zealand Medicines and Medical Devices Safety Authority product register at https://www.medsafe.govt.nz/DbSearch/
- **TGA data** originates from the Australian Therapeutic Goods Administration's ARTG Public Summary at https://www.tga.gov.au/resources/artg

---

### Copyright

The data collected by this project originates from [pharmac.govt.nz](https://www.pharmac.govt.nz/) and is owned by Pharmac. It is licensed under the [Creative Commons Attribution 4.0 International (CC-BY 4.0) licence](https://creativecommons.org/licenses/by/4.0/). Pharmac does not endorse this project or its use of the content. See [Pharmac's copyright statement](https://www.pharmac.govt.nz/about-this-site/copyright) for further details.
