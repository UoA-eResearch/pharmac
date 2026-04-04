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

| Database | Path | Records | Source URL | Retrieved | License |
|----------|------|---------|------------|-----------|---------|
| FDA DrugsFDA | `data/fda/Products.txt`, `data/fda/Submissions.txt`, `data/fda/Applications.txt` | 50,959 products; 3,048 unique active ingredients with approval dates | https://www.fda.gov/media/89850/download | 2026-03-27 | Public domain (US government work) |
| MedSafe Register | `data/medsafe/medsafe_register.csv` | 14,828 products | https://www.medsafe.govt.nz/DbSearch/ (scraped via wildcard ingredient search) | 2026-03-30 | © Medsafe, New Zealand Ministry of Health. Used under [Crown Copyright](https://www.health.govt.nz/about-site/copyright). |
| TGA ARTG | `data/tga/tga_artg.csv` | — | https://www.tga.gov.au/resources/artg | *See note below* | © Commonwealth of Australia. [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/) |

**TGA Note:** The TGA website (tga.gov.au) may block automated access from cloud/CI environments. Use the **Scrape TGA ARTG** GitHub Actions workflow (see below) or run locally:

```bash
# Scrape listing pages — start page is auto-detected from existing row count
python download_databases.py --tga --tga-max-pages 200   # scrape up to 200 pages
python download_databases.py --tga --tga-max-pages 200   # re-run continues from where last left off

# Fetch RegistrationDate for rows that don't have one yet (resumable)
python download_databases.py --tga-dates
```

### GitHub Actions — Scrape TGA ARTG

The [Scrape TGA ARTG](../../actions/workflows/scrape-tga.yml) workflow
(`scrape-tga.yml`) automates both scraping steps within GitHub's 6-hour job
limit:

| Input | Default | Description |
|-------|---------|-------------|
| `run_dates` | `true` | Fetch `RegistrationDate` for rows missing one |
| `dates_delay` | `2.0` | Seconds between product-page requests |
| `run_listings` | `false` | Scrape listing pages to add new ARTG entries |
| `listings_max_pages` | *(all)* | Max pages per run (~2,000 fits in 6 h) |

The listing scrape **automatically resumes from the last scraped page** on each run — there is no need to track or set a start page manually.

**Typical usage to populate the full ~97,000-record ARTG:**

1. Go to *Actions → Scrape TGA ARTG → Run workflow*
2. Enable **Scrape listing pages** and set `listings_max_pages` to `2000`
3. Repeat until all ~3,913 pages are scraped — each run picks up exactly where the last one stopped
4. Finally run with only **Fetch registration dates** enabled to backfill `RegistrationDate`

The workflow also runs automatically **every Sunday** to keep `RegistrationDate` up to date for any rows missing a date.

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

### Match Summary

Running `find_approvals.py` against the 2,015 Pharmac applications using the committed databases gives the following match rates (using substring matching on active ingredient names; fuzzy matching adds additional matches):

| Regulator | Products in database | Pharmac applications matched | Match rate |
|-----------|---------------------|------------------------------|-----------|
| FDA | 50,959 products (3,048 unique active ingredients with approval dates) | ≥ 1,227 / 2,015 | ≥ 60% |
| TGA | 97,593 products (partial — ~100% of ARTG; scrape ongoing) | — | — |
| MedSafe | 14,828 products | ≥ 1,325 / 2,015 | ≥ 65% |

The remaining unmatched applications are typically very new drugs not yet in the databases, NZ-specific formulations, nutritional/dietary products, vaccines, or combination products where the ingredient name differs significantly between databases. The fuzzy matching in `find_approvals.py` recovers additional matches beyond the substring counts above.

### Date Coverage by Dataset

How many rows in each committed database have a date value defined:

| Dataset | Total rows | Rows **with** date | Rows **without** date | Notes |
|---------|-----------|-------------------|----------------------|-------|
| FDA (`Products.txt` linked via `Submissions.txt`) | 50,959 products | 46,127 (90.5%) | 4,832 (9.5%) | Date = earliest `SubmissionStatusDate` where `SubmissionStatus = AP` |
| MedSafe (`medsafe_register.csv`) — Approval date | 14,828 products | 14,828 (100%) | 0 (0%) | All products have an approval date |
| MedSafe (`medsafe_register.csv`) — Notification date | 14,828 products | 10,874 (73.3%) | 3,954 (26.7%) | Notification date is optional and not always recorded |
| TGA (`tga_artg.csv`) — partial scrape | 97,593 products | 22,132 (22.7%) | 75,461 (77.3%) | Registration dates are on individual ARTG product pages, not the listing page; full per-product scrape needed |

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

### Data Provenance and Licensing

- **FDA data** is in the **public domain** (a work of the US federal government) and available from the US Food and Drug Administration at https://www.fda.gov/drugs/drug-approvals-and-databases/drugsfda-data-files. No restrictions on use.
- **MedSafe data** is © Medsafe, New Zealand Ministry of Health. It is sourced from the MedSafe product register at https://www.medsafe.govt.nz/DbSearch/ and is reproduced under [Crown Copyright](https://www.health.govt.nz/about-site/copyright). Medsafe does not endorse this project or its use of the data.
- **TGA data** is © Commonwealth of Australia and is licensed under the [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/) licence. Source: Australian Therapeutic Goods Administration ARTG Public Summary at https://www.tga.gov.au/resources/artg. The TGA does not endorse this project or its use of the data.

---

### Copyright

The data collected by this project originates from [pharmac.govt.nz](https://www.pharmac.govt.nz/) and is owned by Pharmac. It is licensed under the [Creative Commons Attribution 4.0 International (CC-BY 4.0) licence](https://creativecommons.org/licenses/by/4.0/). Pharmac does not endorse this project or its use of the content. See [Pharmac's copyright statement](https://www.pharmac.govt.nz/about-this-site/copyright) for further details.
