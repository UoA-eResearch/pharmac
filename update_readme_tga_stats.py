#!/usr/bin/env python3
"""
Update the TGA statistics in README.md after scraping.

This script reads data/tga/tga_artg.csv and updates the "Date Coverage by Dataset"
table and the Match Summary table in README.md with the current row counts,
percentages, and Pharmac application match counts.
"""

import csv
import re
import sys
from pathlib import Path


def get_tga_stats(csv_path):
    """Calculate TGA statistics from the CSV file."""
    rows = list(csv.DictReader(open(csv_path)))
    total = len(rows)
    with_date = sum(1 for r in rows if r.get('RegistrationDate', '').strip())
    without_date = total - with_date

    if total > 0:
        with_pct = 100.0 * with_date / total
        without_pct = 100.0 * without_date / total
    else:
        with_pct = without_pct = 0.0

    return {
        'total': total,
        'with_date': with_date,
        'without_date': without_date,
        'with_pct': with_pct,
        'without_pct': without_pct
    }


def _split_combination_drug(name):
    """Split a combination drug name into individual components."""
    if not name:
        return []
    parts = re.split(r'[/+]|\band\b|\bwith\b', str(name), flags=re.I)
    return [p.strip() for p in parts if p.strip() and len(p.strip()) > 2]


def _get_primary_ingredient(name):
    """Extract the primary (first) ingredient from a drug name."""
    if not name:
        return ''
    parts = _split_combination_drug(name)
    primary = parts[0] if parts else str(name)
    primary = re.sub(r'\s+\d.*$', '', primary)
    primary = re.sub(r'\s*\(.*\)$', '', primary)
    return primary.strip()


def get_pharmac_match_count(tga_csv_path, pharmac_xlsx_path):
    """Count Pharmac applications that match at least one TGA product via substring search.

    Returns (matched, total) or (None, None) if data cannot be loaded.
    """
    try:
        import openpyxl
    except ImportError:
        print("Warning: openpyxl not available; skipping Pharmac match count", file=sys.stderr)
        return None, None

    # Build combined TGA names string for fast substring lookup
    try:
        tga_names = []
        with open(tga_csv_path, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                name = row.get('Name', '').lower().strip()
                if name:
                    tga_names.append(name)
    except Exception as exc:
        print(f"Warning: Could not read TGA CSV for match counting: {exc}", file=sys.stderr)
        return None, None

    if not tga_names:
        return None, None

    tga_combined = '\n'.join(tga_names)

    # Load Pharmac applications
    try:
        wb = openpyxl.load_workbook(pharmac_xlsx_path, read_only=True)
        ws = wb['Sheet1']
        rows_iter = ws.iter_rows(values_only=True)
        headers = list(next(rows_iter))
        pharmac_rows = [dict(zip(headers, row)) for row in rows_iter]
    except Exception as exc:
        print(f"Warning: Could not read Pharmac applications for match counting: {exc}", file=sys.stderr)
        return None, None

    total = len(pharmac_rows)
    matched = 0

    for row in pharmac_rows:
        chemical_name = str(row.get('Chemical_Name__c', '') or '')
        brand_name = str(row.get('Brand_Name__c', '') or '')

        found = False

        ingredients = _split_combination_drug(chemical_name)
        primary = _get_primary_ingredient(chemical_name)
        all_terms = ingredients + ([primary] if primary and primary not in ingredients else [])

        for ing in all_terms:
            ing_lower = ing.lower().strip()
            if len(ing_lower) < 3:
                continue
            if ing_lower in tga_combined:
                found = True
                break

        if not found and brand_name:
            brand_lower = brand_name.lower().strip()
            if len(brand_lower) >= 3 and brand_lower in tga_combined:
                found = True

        if found:
            matched += 1

    return matched, total


def update_readme(readme_path, csv_path, pharmac_xlsx_path=None):
    """Update the README.md file with current TGA statistics."""
    stats = get_tga_stats(csv_path)

    # Read the README
    with open(readme_path, 'r') as f:
        content = f.read()

    # Update 1: The TGA row in the "Date Coverage by Dataset" table
    # This matches the line that starts with "| TGA (`tga_artg.csv`)"
    date_coverage_row = (
        f"| TGA (`tga_artg.csv`) — partial scrape | "
        f"{stats['total']:,} products | "
        f"{stats['with_date']:,} ({stats['with_pct']:.1f}%) | "
        f"{stats['without_date']:,} ({stats['without_pct']:.1f}%) | "
        f"Registration dates are on individual ARTG product pages, not the listing page; full per-product scrape needed |"
    )
    pattern1 = r'\| TGA \(`tga_artg\.csv`\)[^\n]*\|[^\n]*\|[^\n]*\|[^\n]*\|[^\n]*\|'
    updated_content, num_subs1 = re.subn(pattern1, date_coverage_row, content)

    if num_subs1 == 0:
        print("Error: Could not find TGA row in 'Date Coverage by Dataset' table", file=sys.stderr)
        return False

    # Update 2: The TGA row in the match rate table (earlier in the README)
    # This matches "| TGA | 6,950 products (partial..." or similar
    # Calculate percentage of total ARTG based on ~3913 pages * 25 records/page = ~97,825
    artg_total = 97825  # Approximate total ARTG size based on pagination
    pct_of_artg = 100.0 * stats['total'] / artg_total

    # Compute Pharmac match count if possible
    match_str = "—"
    rate_str = "—"
    if pharmac_xlsx_path is not None and Path(pharmac_xlsx_path).exists():
        match_count, pharmac_total = get_pharmac_match_count(csv_path, pharmac_xlsx_path)
        if match_count is not None and pharmac_total:
            match_pct = 100 * match_count // pharmac_total
            match_str = f"≥ {match_count:,} / {pharmac_total:,}"
            rate_str = f"≥ {match_pct}%"
            print(f"Pharmac match count: {match_count:,} / {pharmac_total:,} ({match_pct}%)")

    match_rate_row = (
        f"| TGA | {stats['total']:,} products (partial — ~{pct_of_artg:.0f}% of ARTG; scrape ongoing) | "
        f"{match_str} | {rate_str} |"
    )
    pattern2 = r'\| TGA \| [0-9,]+ products \(partial[^\n]*\|[^\n]*\|[^\n]*\|'
    updated_content, num_subs2 = re.subn(pattern2, match_rate_row, updated_content)

    if num_subs2 == 0:
        print("Warning: Could not find TGA row in match rate table (may not exist)", file=sys.stderr)

    # Write the updated content back
    with open(readme_path, 'w') as f:
        f.write(updated_content)

    total_updates = num_subs1 + num_subs2
    print(f"Updated README.md ({total_updates} tables): {stats['total']:,} total rows, {stats['with_date']:,} ({stats['with_pct']:.1f}%) with dates")
    return True


def main():
    """Main entry point."""
    repo_root = Path(__file__).parent
    readme_path = repo_root / 'README.md'
    csv_path = repo_root / 'data' / 'tga' / 'tga_artg.csv'
    pharmac_xlsx_path = repo_root / 'Pharmac applications.xlsx'

    if not csv_path.exists():
        print(f"Error: CSV file not found at {csv_path}", file=sys.stderr)
        sys.exit(1)

    if not readme_path.exists():
        print(f"Error: README.md not found at {readme_path}", file=sys.stderr)
        sys.exit(1)

    if update_readme(readme_path, csv_path, pharmac_xlsx_path):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
