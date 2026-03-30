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


def _make_tga_driver():
    """Create a WebDriver for TGA scraping.

    Tries in order:
    1. undetected-chromedriver + Xvfb virtual display  (bypasses Akamai CDN)
    2. undetected-chromedriver headless
    3. Standard selenium Chrome headless (fallback)
    """
    import subprocess, shutil

    # --- Strategy 1: undetected-chromedriver + Xvfb ---
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

        driver = uc.Chrome(options=opts, version_main=146)
        driver.set_page_load_timeout(60)
        driver._xvfb_proc = xvfb_proc
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


def download_tga(max_pages=None):
    """Scrape TGA ARTG listing pages and write data/tga/tga_artg.csv.

    Parameters
    ----------
    max_pages : int or None
        Maximum pages to scrape (None = all ~3913 pages).
        Each page has 25 records. Use e.g. 200 for a quick partial run.

    Notes
    -----
    Requires ``undetected-chromedriver`` (preferred) or ``selenium`` plus
    Google Chrome and ChromeDriver. The TGA website uses Akamai CDN which
    blocks plain requests and standard headless Chrome from cloud/CI IPs;
    undetected-chromedriver with a virtual Xvfb display bypasses this.
    Run from a local machine if the cloud IP is still blocked.

    Progress is saved after each page so the run can be interrupted/resumed
    (delete tga_artg.csv to restart from scratch).
    """
    os.makedirs(TGA_DIR, exist_ok=True)
    output_file = os.path.join(TGA_DIR, "tga_artg.csv")

    if os.path.exists(output_file):
        print("TGA data file already exists. Skipping download.")
        print(f"  Delete {output_file} to force a re-download.")
        return

    if max_pages is None:
        max_pages = TGA_TOTAL_PAGES

    print("Scraping TGA ARTG via Selenium/undetected-chromedriver...")
    print(f"  Source: {TGA_ARTG_LISTING_URL}")
    print(f"  Max pages: {max_pages} (~{max_pages * 25:,} records)")

    try:
        driver = _make_tga_driver()
    except RuntimeError as exc:
        print(f"  ERROR: {exc}")
        return

    fieldnames = ["ARTG_ID", "Name", "RegistrationDate"]
    all_records, seen_ids, consecutive_blocks = [], set(), 0

    try:
        for page_num in range(1, max_pages + 1):
            url = f"{TGA_ARTG_LISTING_URL}?page={page_num}"
            print(f"  [{page_num}/{max_pages}] {url}", flush=True)

            try:
                driver.get(url)
                # Wait up to 25s for real page content
                deadline = time.time() + 25
                while time.time() < deadline:
                    src = driver.page_source
                    if "summary__content" in src or len(src) < 10_000:
                        break
                    time.sleep(0.5)
            except Exception as exc:
                print(f"    Load error: {exc} — restarting driver")
                _quit_tga_driver(driver)
                driver = _make_tga_driver()
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
                    print(
                        "    Too many consecutive blocks — "
                        "re-run from a local machine or try later."
                    )
                    break
                _quit_tga_driver(driver)
                time.sleep(TGA_BLOCK_BACKOFF)
                driver = _make_tga_driver()
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

            # Save after every page so progress is preserved
            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_records)

            if not records:
                print("    No records — last page reached.")
                break

            time.sleep(TGA_PAGE_DELAY)

    finally:
        _quit_tga_driver(driver)

    print(f"\nTGA scrape complete: {len(all_records):,} records → {output_file}")


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
    parser.add_argument("--medsafe", action="store_true", help="Build MedSafe database")
    parser.add_argument("--all", action="store_true", help="Download all databases")
    args = parser.parse_args()

    # Default: download all if no flags specified
    do_all = args.all or not (args.fda or args.tga or args.medsafe)

    if do_all or args.fda:
        download_fda()

    if do_all or args.tga:
        download_tga(max_pages=args.tga_max_pages)

    if do_all or args.medsafe:
        download_medsafe()

    print("\nAll requested databases have been downloaded/built.")


if __name__ == "__main__":
    main()
