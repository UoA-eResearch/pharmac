#!/usr/bin/env python3
"""
Download and build drug approval databases from FDA, TGA, and MedSafe.

This script downloads the necessary databases to support find_approvals.py:

- FDA (US Food and Drug Administration):
  Source: https://www.fda.gov/media/89850/download
  Data: DrugsFDA bulk data files (Products.txt, Submissions.txt, Applications.txt)

- TGA (Australian Therapeutic Goods Administration):
  Source: https://www.tga.gov.au/resources/artg
  Note: The TGA ARTG can be downloaded from the TGA website. This script
  provides download code but the TGA website may block automated access from
  some environments. Download manually if needed.

- MedSafe (New Zealand Medicines and Medical Devices Safety Authority):
  Source: https://www.medsafe.govt.nz/DbSearch/
  Data: Scraped from MedSafe product search (product register)

Usage:
    python download_databases.py [--fda] [--tga] [--medsafe] [--all]

If no flags are given, all databases are downloaded/built.
"""

import argparse
import csv
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
# TGA Download
# =============================================================================

def download_tga():
    """
    Download TGA ARTG data.

    NOTE: The TGA website (www.tga.gov.au) may block automated access from
    cloud/CI environments due to CDN restrictions. If this script fails,
    download the data manually:

    1. Go to https://www.tga.gov.au/resources/artg
    2. Download the ARTG Public Summary extract (Excel/CSV format)
    3. Save as data/tga/tga_artg.csv

    Alternatively, the ARTG data may be available via:
    - data.gov.au (search for "ARTG" or "therapeutic goods")
    - TGA's product search: https://www.tga.gov.au/products/artg-public-summary
    """
    os.makedirs(TGA_DIR, exist_ok=True)
    output_file = os.path.join(TGA_DIR, "tga_artg.csv")

    if os.path.exists(output_file):
        print("TGA data file already exists. Skipping download.")
        return

    print("Attempting to download TGA data...")
    print(f"  Source: {TGA_URL}")

    # Try to access TGA - note this may fail from some environments
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        resp = requests.get(TGA_URL, headers=headers, timeout=30)
        resp.raise_for_status()
        # Parse the page to find download links
        # Look for CSV/Excel download links
        links = re.findall(r'href="([^"]*(?:artg|ARTG)[^"]*\.(?:csv|xlsx|zip))"', resp.text)
        if links:
            for link in links:
                if not link.startswith("http"):
                    link = "https://www.tga.gov.au" + link
                print(f"  Found download link: {link}")
                # Download the file
                dl_resp = requests.get(link, headers=headers, timeout=120)
                dl_resp.raise_for_status()
                # Save and convert if needed
                if link.endswith(".csv"):
                    with open(output_file, "wb") as f:
                        f.write(dl_resp.content)
                    print(f"TGA data saved to {output_file}")
                    return
        print("  No direct download links found on TGA page.")
        print("  Please download TGA data manually - see instructions in docstring.")
    except Exception as e:
        print(f"  TGA download failed: {e}")
        print("  Please download TGA data manually - see instructions in docstring.")
        print("  TGA website may be blocking automated access from this environment.")


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
    parser.add_argument("--tga", action="store_true", help="Download TGA data")
    parser.add_argument("--medsafe", action="store_true", help="Build MedSafe database")
    parser.add_argument("--all", action="store_true", help="Download all databases")
    args = parser.parse_args()

    # Default: download all if no flags specified
    do_all = args.all or not (args.fda or args.tga or args.medsafe)

    if do_all or args.fda:
        download_fda()

    if do_all or args.tga:
        download_tga()

    if do_all or args.medsafe:
        download_medsafe()

    print("\nAll requested databases have been downloaded/built.")


if __name__ == "__main__":
    main()
