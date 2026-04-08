#!/usr/bin/env python3
"""
Download and build drug approval databases from FDA, TGA, and MedSafe.

This script downloads the necessary databases to support find_approvals.py:

- FDA (US Food and Drug Administration):
  Source: https://www.fda.gov/media/89850/download
  Data: DrugsFDA bulk data files (Products.txt, Submissions.txt, Applications.txt)

- TGA (Australian Therapeutic Goods Administration):
  Source: https://www.tga.gov.au/resources/artg
  Uses undetected-chromedriver (with Xvfb virtual display) or standard Selenium
  Chrome headless to scrape the ARTG listing pages. The TGA website uses Akamai
  CDN which may rate-limit plain requests or standard headless Chrome; run from
  a local machine if blocked. Requires google-chrome and chromedriver.

- MedSafe (New Zealand Medicines and Medical Devices Safety Authority):
  Source: https://www.medsafe.govt.nz/DbSearch/
  Data: Scraped from MedSafe product search (product register)

Usage:
    python download_databases.py [--fda] [--tga] [--medsafe] [--all]
    python download_databases.py --tga --tga-max-pages 200

If no flags are given, all databases are downloaded/built.
"""

import argparse
import csv
import datetime
import io
import os
import re
import time
import zipfile
from html.parser import HTMLParser

import requests

# --- Output paths ---
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
FDA_DIR = os.path.join(DATA_DIR, "fda")
TGA_DIR = os.path.join(DATA_DIR, "tga")
MEDSAFE_DIR = os.path.join(DATA_DIR, "medsafe")

FDA_URL = "https://www.fda.gov/media/89850/download"
TGA_URL = "https://www.tga.gov.au/resources/artg"  # See note below
MEDSAFE_BASE_URL = "https://www.medsafe.govt.nz/DbSearch/"
MEDSAFE_SEARCH_URL = "https://www.medsafe.govt.nz/DbSearch/Default.asp"
# Azure-hosted backend (fallback if main URL is blocked):
MEDSAFE_AZURE_BASE = "https://azapp-medsafe-dbsearch.azurewebsites.net/DbSearch/"
MEDSAFE_AZURE_SEARCH = "https://azapp-medsafe-dbsearch.azurewebsites.net/DbSearch/Default.asp"


# =============================================================================
# FDA Download
# =============================================================================

def download_fda():
    """Download FDA DrugsFDA bulk data files."""
    os.makedirs(FDA_DIR, exist_ok=True)

    needed = ["Products.txt", "Submissions.txt", "Applications.txt"]
    if all(os.path.exists(os.path.join(FDA_DIR, f)) for f in needed):
        print("FDA data files already exist. Skipping download.")
        return

    print(f"Downloading FDA data from {FDA_URL} ...")
    resp = requests.get(FDA_URL, stream=True, timeout=120)
    resp.raise_for_status()

    # The response is a zip file
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        for name in needed:
            if name in zf.namelist():
                print(f"  Extracting {name}...")
                zf.extract(name, FDA_DIR)
            else:
                print(f"  WARNING: {name} not found in zip")

    print("FDA download complete.")


# =============================================================================
# TGA Download (Selenium / undetected-chromedriver scraper)
# =============================================================================

TGA_ARTG_LISTING_URL = "https://www.tga.gov.au/resources/artg"
TGA_TOTAL_PAGES = 3913          # approx pages as of 2026 (25 items/page)
TGA_PAGE_DELAY = 10             # seconds between page requests
TGA_MAX_CONSECUTIVE_BLOCKS = 5  # give up after this many consecutive blocks
TGA_BLOCK_BACKOFF = 60          # seconds to wait after a block


def _make_tga_driver(force_selenium=False):
    """Create a WebDriver for TGA scraping.

    Tries in order:
    1. undetected-chromedriver (optionally with Xvfb virtual display to bypass Akamai CDN)
       — skipped when *force_selenium* is ``True``
    2. Standard selenium Chrome headless (fallback)

    The returned driver has two extra attributes set by this function:

    * ``_xvfb_proc`` – the Xvfb :class:`subprocess.Popen` object (or ``None``).
    * ``_is_uc`` – ``True`` when undetected-chromedriver was used, ``False``
      for standard selenium.  Callers can inspect this to decide whether to
      retry with ``force_selenium=True`` after too many blocks.
    """
    import subprocess, shutil

    # --- Strategy 1: undetected-chromedriver + Xvfb ---
    if not force_selenium:
        try:
            import undetected_chromedriver as uc  # noqa: F401

            xvfb_proc = None
            xvfb_path = shutil.which("Xvfb")
            if xvfb_path:
                xvfb_proc = subprocess.Popen(
                    [xvfb_path, ":99", "-screen", "0", "1920x1080x24"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                os.environ["DISPLAY"] = ":99"
                time.sleep(1)

            opts = uc.ChromeOptions()
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--window-size=1920,1080")

            try:
                # Detect the installed Chrome version to ensure ChromeDriver matches.
                # This prevents version mismatch errors like "ChromeDriver only supports
                # Chrome version X" when the installed Chrome is version Y.
                chrome_version = None
                chrome_path = shutil.which("google-chrome") or shutil.which("chrome")
                if chrome_path:
                    try:
                        version_output = subprocess.check_output(
                            [chrome_path, "--version"],
                            stderr=subprocess.DEVNULL,
                            text=True,
                        ).strip()
                        # Parse version like "Google Chrome 146.0.7680.0" -> 146
                        match = re.search(r"(\d+)\.", version_output)
                        if match:
                            chrome_version = int(match.group(1))
                            print(f"  Detected Chrome version: {chrome_version}")
                    except Exception:
                        pass

                # Pass version_main to ensure ChromeDriver matches installed Chrome
                if chrome_version:
                    driver = uc.Chrome(options=opts, version_main=chrome_version)
                else:
                    # Fallback to auto-detection if version detection failed
                    driver = uc.Chrome(options=opts)
            except Exception:
                # Chrome launch failed — terminate any Xvfb we started so it
                # doesn't leak as a background process on the runner.
                if xvfb_proc is not None:
                    xvfb_proc.terminate()
                    xvfb_proc.wait()
                raise

            driver.set_page_load_timeout(60)
            driver._xvfb_proc = xvfb_proc
            driver._is_uc = True
            print("  Using undetected-chromedriver" + (" + Xvfb" if xvfb_proc else ""))
            return driver

        except Exception as exc:
            print(f"  undetected-chromedriver failed ({exc}), falling back to selenium")

    # --- Strategy 2/3: standard selenium ---
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
    except ImportError:
        raise RuntimeError(
            "selenium is required. Install with: pip install selenium"
        )

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(60)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    driver._xvfb_proc = None
    driver._is_uc = False
    print("  Using standard selenium headless Chrome")
    return driver


def _quit_tga_driver(driver):
    """Quit driver and terminate any Xvfb process it owns."""
    try:
        driver.quit()
    except Exception:
        pass
    try:
        xvfb = getattr(driver, "_xvfb_proc", None)
        if xvfb is not None:
            xvfb.terminate()
    except Exception:
        pass


def _tga_page_is_blocked(src):
    """True if the page source is a block/challenge page rather than real ARTG content."""
    return "summary__content" not in src


def _tga_product_page_is_blocked(src):
    """True if an individual ARTG product page is a block/challenge page."""
    return "health-field__label" not in src


def _tga_product_page_not_found(src):
    """True if an individual ARTG product page returns 'Page not found'."""
    return "Page not found" in src and "Sorry, we can't find that page" in src


def _parse_tga_artg_product_date(src):
    """Extract the ARTG Date from an individual product page source.

    Returns the date as an ISO-8601 string (``YYYY-MM-DD``) or an empty
    string if no date could be found.
    """
    # Prefer the machine-readable datetime attribute on the <time> element
    m = re.search(r'ARTG Date.*?<time[^>]+datetime="(\d{4}-\d{2}-\d{2})', src, re.DOTALL)
    if m:
        return m.group(1)
    # Fall back to the human-readable date text
    m = re.search(r'ARTG Date.*?(\d{1,2}\s+\w+\s+\d{4})', src, re.DOTALL)
    if m:
        try:
            return datetime.datetime.strptime(m.group(1), "%d %B %Y").strftime("%Y-%m-%d")
        except ValueError:
            return m.group(1)
    return ""


def _parse_tga_artg_page(src):
    """Parse one ARTG listing page; return list of record dicts."""
    records = []
    for block in re.split(r'class="summary__content', src)[1:]:
        link_m = re.search(r'href="/resources/artg/(\d+)"[^>]*>([^<]+)</a>', block)
        if not link_m:
            continue
        artg_id, name = link_m.group(1), link_m.group(2).strip()
        date_m = re.search(r"(\d{1,2}\s+\w+\s+\d{4})", block[:600])
        date_iso = ""
        if date_m:
            try:
                date_iso = datetime.datetime.strptime(
                    date_m.group(1), "%d %B %Y"
                ).strftime("%Y-%m-%d")
            except ValueError:
                date_iso = date_m.group(1)
        records.append({"ARTG_ID": artg_id, "Name": name, "RegistrationDate": date_iso})
    return records


def download_tga(max_pages=None, start_page=None):
    """Scrape TGA ARTG listing pages and write data/tga/tga_artg.csv.

    Parameters
    ----------
    max_pages : int or None
        Maximum pages to scrape (None = all ~3913 pages).
        Each page has 25 records. Use e.g. 200 for a quick partial run.
    start_page : int or None
        Page number to start from.  When ``None`` (the default) the value is
        inferred automatically from the number of rows already in
        ``tga_artg.csv``: ``start_page = max(1, existing_rows // 25)``.
        This lets every run resume exactly where the last one left off without
        any manual bookkeeping.  Pass an explicit integer to override.

    Notes
    -----
    Requires ``undetected-chromedriver`` (preferred) or ``selenium`` plus
    Google Chrome and ChromeDriver. The TGA website uses Akamai CDN which
    blocks plain requests and standard headless Chrome from cloud/CI IPs;
    undetected-chromedriver with a virtual Xvfb display bypasses this.
    Run from a local machine if the cloud IP is still blocked.

    If ``data/tga/tga_artg.csv`` already exists, its rows are loaded first
    so that IDs already collected are not duplicated. New records are
    appended to the file as scraping proceeds.
    """
    os.makedirs(TGA_DIR, exist_ok=True)
    output_file = os.path.join(TGA_DIR, "tga_artg.csv")

    fieldnames = ["ARTG_ID", "Name", "RegistrationDate"]
    all_records: list = []
    seen_ids: set = set()

    # Seed from existing data so we never duplicate IDs and so any
    # dates already fetched are preserved when re-running.
    if os.path.exists(output_file):
        with open(output_file, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                all_records.append(row)
                seen_ids.add(row["ARTG_ID"])
        print(f"  Loaded {len(all_records):,} existing rows from {output_file}")

    # Auto-detect start page from existing row count when not specified.
    # Each listing page has 25 entries, so existing_rows // 25 gives the last
    # fully-scraped page.  We back up one page to avoid missing a partial last
    # page (safe because duplicate IDs are skipped).
    if start_page is None:
        if all_records:
            start_page = max(1, len(all_records) // 25)
            print(f"  Auto-detected start page: {start_page} ({len(all_records):,} existing rows)")
        else:
            start_page = 1

    if max_pages is None:
        max_pages = TGA_TOTAL_PAGES

    end_page = start_page + max_pages - 1
    print("Scraping TGA ARTG via Selenium/undetected-chromedriver...")
    print(f"  Source: {TGA_ARTG_LISTING_URL}")
    print(f"  Pages {start_page}–{end_page} (~{max_pages * 25:,} records max)")

    try:
        driver = _make_tga_driver()
    except RuntimeError as exc:
        print(f"  ERROR: {exc}")
        return

    consecutive_blocks = 0

    # Prepare the output file: write header now if the file doesn't exist yet,
    # so we can append individual pages' records without rewriting everything.
    if not os.path.exists(output_file):
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=fieldnames).writeheader()

    try:
        for page_num in range(start_page, end_page + 1):
            url = f"{TGA_ARTG_LISTING_URL}?page={page_num}"
            print(f"  [{page_num}/{end_page}] {url}", flush=True)

            try:
                driver.get(url)
                # Wait up to 25s for real page content
                deadline = time.time() + 25
                while time.time() < deadline:
                    src = driver.page_source
                    if "summary__content" in src or len(src) > 10_000:
                        break
                    time.sleep(0.5)
            except Exception as exc:
                print(f"    Load error: {exc} — restarting driver")
                _is_uc = getattr(driver, "_is_uc", True)
                _quit_tga_driver(driver)
                driver = _make_tga_driver(force_selenium=not _is_uc)
                time.sleep(TGA_BLOCK_BACKOFF)
                continue

            src = driver.page_source

            if _tga_page_is_blocked(src):
                consecutive_blocks += 1
                print(
                    f"    Blocked ({consecutive_blocks}/{TGA_MAX_CONSECUTIVE_BLOCKS}). "
                    f"Sleeping {TGA_BLOCK_BACKOFF}s..."
                )
                if consecutive_blocks >= TGA_MAX_CONSECUTIVE_BLOCKS:
                    if getattr(driver, "_is_uc", False):
                        print(
                            "    Too many consecutive blocks with undetected-chromedriver "
                            "— switching to standard selenium..."
                        )
                        _quit_tga_driver(driver)
                        driver = _make_tga_driver(force_selenium=True)
                        consecutive_blocks = 0
                        continue
                    print(
                        "    Too many consecutive blocks — "
                        "re-run from a local machine or try later."
                    )
                    break
                _quit_tga_driver(driver)
                time.sleep(TGA_BLOCK_BACKOFF)
                _is_uc = getattr(driver, "_is_uc", True)
                driver = _make_tga_driver(force_selenium=not _is_uc)
                continue

            consecutive_blocks = 0
            records = _parse_tga_artg_page(src)
            new_records = [r for r in records if r["ARTG_ID"] not in seen_ids]
            for r in new_records:
                seen_ids.add(r["ARTG_ID"])
            all_records.extend(new_records)

            print(
                f"    {len(new_records)} new (page: {len(records)}, "
                f"total: {len(all_records)})"
            )

            # Append only the new records for this page so progress is
            # preserved without rewriting the full file every iteration
            # (O(n) total I/O instead of O(n²)).
            if new_records:
                with open(output_file, "a", newline="", encoding="utf-8") as f:
                    csv.DictWriter(f, fieldnames=fieldnames).writerows(new_records)

            if not records:
                print("    No records — last page reached.")
                break

            time.sleep(TGA_PAGE_DELAY)

    finally:
        _quit_tga_driver(driver)

    print(f"\nTGA scrape complete: {len(all_records):,} records → {output_file}")


def _write_tga_csv_atomic(output_file, fieldnames, rows, artg_dates):
    """Write updated rows to *output_file* using an atomic temp-file rename.

    Builds the full CSV in a temporary file next to *output_file*, then
    replaces the destination with a single ``os.replace()`` call so the file
    is never left in a partial state even if the process is interrupted.
    """
    tmp_path = output_file + ".tmp"
    updated = [
        {"ARTG_ID": r["ARTG_ID"], "Name": r["Name"],
         "RegistrationDate": artg_dates.get(r["ARTG_ID"], "")}
        for r in rows
    ]
    with open(tmp_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated)
    os.replace(tmp_path, output_file)


def download_tga_dates(delay=3.0):
    """Fetch the ARTG Date for every row in tga_artg.csv that has no date.

    Visits each individual product page at
    ``https://www.tga.gov.au/resources/artg/<ARTG_ID>``, extracts the
    ``ARTG Date`` field, and writes the result back to tga_artg.csv.

    Parameters
    ----------
    delay : float
        Seconds to pause between product-page requests (default: 3 s).
        Individual product pages are less aggressively rate-limited than
        the paginated listing, so a shorter delay is safe.

    Notes
    -----
    The function is resumable: rows that already have a date are skipped
    and rows that could not be fetched (blocked/error) are left empty so
    that re-running the script will retry them.
    """
    output_file = os.path.join(TGA_DIR, "tga_artg.csv")
    if not os.path.exists(output_file):
        print(f"No TGA data file found at {output_file}. Run --tga first.")
        return

    # Read existing data
    with open(output_file, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    fieldnames = ["ARTG_ID", "Name", "RegistrationDate"]
    missing = [r for r in rows if not r.get("RegistrationDate", "").strip()]
    print(
        f"Fetching ARTG dates for {len(missing):,} / {len(rows):,} rows "
        f"(already have {len(rows) - len(missing):,})..."
    )
    if not missing:
        print("All rows already have dates.")
        return

    try:
        driver = _make_tga_driver()
    except RuntimeError as exc:
        print(f"  ERROR: {exc}")
        return

    artg_dates = {r["ARTG_ID"]: r.get("RegistrationDate", "") for r in rows}
    consecutive_blocks = 0
    fetched = 0

    try:
        for i, row in enumerate(missing):
            artg_id = row["ARTG_ID"]
            url = f"{TGA_ARTG_LISTING_URL}/{artg_id}"
            print(f"  [{i + 1}/{len(missing)}] {url}", flush=True)

            try:
                driver.get(url)
                deadline = time.time() + 25
                while time.time() < deadline:
                    src = driver.page_source
                    if "health-field__label" in src or len(src) > 10_000:
                        break
                    time.sleep(0.5)
            except Exception as exc:
                print(f"    Load error: {exc} — restarting driver")
                _is_uc = getattr(driver, "_is_uc", True)
                _quit_tga_driver(driver)
                driver = _make_tga_driver(force_selenium=not _is_uc)
                time.sleep(TGA_BLOCK_BACKOFF)
                continue

            src = driver.page_source

            if _tga_product_page_not_found(src):
                print(f"    Page not found — skipping")
                # Leave the date empty for this product
                artg_dates[artg_id] = ""
                time.sleep(delay)
                continue

            if _tga_product_page_is_blocked(src):
                consecutive_blocks += 1
                print(
                    f"    Blocked ({consecutive_blocks}/{TGA_MAX_CONSECUTIVE_BLOCKS}). "
                    f"Sleeping {TGA_BLOCK_BACKOFF}s..."
                )
                if consecutive_blocks >= TGA_MAX_CONSECUTIVE_BLOCKS:
                    if getattr(driver, "_is_uc", False):
                        print(
                            "    Too many consecutive blocks with undetected-chromedriver "
                            "— switching to standard selenium..."
                        )
                        _quit_tga_driver(driver)
                        driver = _make_tga_driver(force_selenium=True)
                        consecutive_blocks = 0
                        continue
                    print(
                        "    Too many consecutive blocks — "
                        "re-run from a local machine or try later."
                    )
                    break
                _quit_tga_driver(driver)
                time.sleep(TGA_BLOCK_BACKOFF)
                _is_uc = getattr(driver, "_is_uc", True)
                driver = _make_tga_driver(force_selenium=not _is_uc)
                continue

            consecutive_blocks = 0
            date_val = _parse_tga_artg_product_date(src)
            artg_dates[artg_id] = date_val
            fetched += 1

            if (i + 1) % 100 == 0 or date_val:
                print(f"    date={date_val!r}  (fetched {fetched} so far)")

            # Checkpoint every 500 successful fetches using an atomic rename
            # so the full CSV is written infrequently and the file is never
            # left in a partial state.
            if fetched % 500 == 0:
                _write_tga_csv_atomic(output_file, fieldnames, rows, artg_dates)

            time.sleep(delay)

    finally:
        _quit_tga_driver(driver)

    # Final save (atomic)
    _write_tga_csv_atomic(output_file, fieldnames, rows, artg_dates)

    with_date = sum(1 for r in updated if r["RegistrationDate"])
    print(
        f"\nTGA dates complete: {with_date:,}/{len(updated):,} rows now have a date "
        f"→ {output_file}"
    )


# =============================================================================
# MedSafe Scraper
# =============================================================================

class MedSafeTableParser(HTMLParser):
    """Parser for MedSafe product search results HTML tables."""

    def __init__(self):
        super().__init__()
        self.in_result_table = False
        self.current_row = []
        self.current_cell = ""
        self.records = []
        self.headers = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "table" and attrs_dict.get("border") == "1":
            self.in_result_table = True
        elif tag in ("td", "th") and self.in_result_table:
            self.current_cell = ""

    def handle_endtag(self, tag):
        if tag == "table":
            self.in_result_table = False
        elif tag in ("td", "th") and self.in_result_table:
            self.current_row.append(self.current_cell.strip())
        elif tag == "tr" and self.in_result_table:
            if self.current_row:
                if not self.headers:
                    self.headers = self.current_row
                else:
                    self.records.append(dict(zip(self.headers, self.current_row)))
            self.current_row = []

    def handle_data(self, data):
        if self.in_result_table:
            self.current_cell += data


def _get_medsafe_session():
    """Get a working MedSafe session, trying main URL first then Azure fallback."""
    for base_url, search_url in [
        (MEDSAFE_BASE_URL, MEDSAFE_SEARCH_URL),
        (MEDSAFE_AZURE_BASE, MEDSAFE_AZURE_SEARCH),
    ]:
        try:
            session = requests.Session()
            resp = session.get(base_url, timeout=30)
            if resp.status_code == 200:
                return session, base_url, search_url
        except Exception:
            pass
    raise RuntimeError(
        "Cannot connect to MedSafe. Both primary and Azure URLs are unavailable.\n"
        "Please try running this script from a different network."
    )


def search_medsafe(session, ingredient_query, base_url=None, search_url=None):
    """Search MedSafe for products containing the given ingredient.

    Returns a list of product records (dicts).
    """
    if base_url is None:
        base_url = MEDSAFE_BASE_URL
    if search_url is None:
        search_url = MEDSAFE_SEARCH_URL
    data = {
        "optSearch": "Product",
        "txtIngredient": ingredient_query,
        "txtTradeName": "",
        "txtSponsor": "",
        "txtFromDate": "",  # No date filter - get all products
        "txtToDate": "",
        "cmdSearch": "Submit",
    }
    headers_dict = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": base_url,
    }
    try:
        resp = session.post(search_url, data=data, headers=headers_dict, timeout=120)
        p = MedSafeTableParser()
        p.feed(resp.text)
        return p.records
    except Exception as e:
        print(f"  Error searching MedSafe for '{ingredient_query}': {e}")
        return []


def download_medsafe():
    """Build a comprehensive MedSafe product register by scraping all products.

    Uses alphabetical wildcard searches (a%, b%, ... z%, 0%, ... 9%) to
    retrieve all products from the MedSafe product register.

    Note: MedSafe may block bulk scraping after many requests from the same IP.
    The script tries the main MedSafe URL first, then falls back to the
    Azure-hosted backend (azapp-medsafe-dbsearch.azurewebsites.net).
    """
    os.makedirs(MEDSAFE_DIR, exist_ok=True)
    output_file = os.path.join(MEDSAFE_DIR, "medsafe_register.csv")

    if os.path.exists(output_file):
        print("MedSafe database already exists. Skipping download.")
        return

    print("Building MedSafe product register...")
    print("  This will take approximately 30-40 minutes due to server response times.")

    # Establish session (with fallback to Azure)
    session, base_url, search_url = _get_medsafe_session()
    print(f"  Using: {base_url}")

    all_records = []
    seen_products = set()

    # Search using single-letter + wildcard to get all products alphabetically
    search_terms = [f"{c}%" for c in "abcdefghijklmnopqrstuvwxyz0123456789"]
    total = len(search_terms)

    for i, term in enumerate(search_terms):
        print(f"  [{i+1}/{total}] Searching for '{term}'...", flush=True)
        # Refresh session for each search to avoid session expiry
        try:
            session, base_url, search_url = _get_medsafe_session()
        except RuntimeError as e:
            print(f"  Session refresh failed: {e}")
            break
        records = search_medsafe(session, term, base_url, search_url)

        new_count = 0
        for record in records:
            product = record.get("Product", "")
            if product not in seen_products:
                seen_products.add(product)
                all_records.append(record)
                new_count += 1

        print(f"    Got {len(records)} products, {new_count} new. Total: {len(all_records)}")

        # Save intermediate results after each letter
        if all_records:
            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "Product",
                        "Active ingredients",
                        "Sponsor",
                        "Status",
                        "Approval date",
                        "Notification date",
                    ],
                )
                writer.writeheader()
                writer.writerows(all_records)

        time.sleep(1)  # Be polite to the server

    print(f"\nMedSafe database complete: {len(all_records)} products")
    print(f"Saved to {output_file}")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fda", action="store_true", help="Download FDA data")
    parser.add_argument("--tga", action="store_true", help="Scrape TGA ARTG via Selenium")
    parser.add_argument(
        "--tga-max-pages", type=int, default=None, metavar="N",
        help="Max ARTG pages to scrape (default: all ~3913). "
             "E.g. --tga-max-pages 200 ≈ 5,000 records in ~30 min."
    )
    parser.add_argument(
        "--tga-start-page", type=int, default=None, metavar="N",
        help="Listing page number to start from. "
             "Defaults to auto-detection from the existing row count "
             "(existing_rows // 25), so re-running always continues from "
             "where the last run left off."
    )
    parser.add_argument(
        "--tga-dates", action="store_true",
        help="Fetch ARTG Date for rows in tga_artg.csv that have no date yet"
    )
    parser.add_argument(
        "--tga-dates-delay", type=float, default=3.0, metavar="SECS",
        help="Seconds between individual product-page requests when --tga-dates "
             "is used (default: 3.0)"
    )
    parser.add_argument("--medsafe", action="store_true", help="Build MedSafe database")
    parser.add_argument("--all", action="store_true", help="Download all databases")
    args = parser.parse_args()

    # Default: download all if no flags specified
    do_all = args.all or not (args.fda or args.tga or args.tga_dates or args.medsafe)

    if do_all or args.fda:
        download_fda()

    if do_all or args.tga:
        download_tga(max_pages=args.tga_max_pages, start_page=args.tga_start_page)

    if args.tga_dates:
        download_tga_dates(delay=args.tga_dates_delay)

    if do_all or args.medsafe:
        download_medsafe()

    print("\nAll requested databases have been downloaded/built.")


if __name__ == "__main__":
    main()
