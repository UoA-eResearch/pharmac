#!/usr/bin/env python3
"""
Update the TGA statistics in README.md after scraping.

This script reads data/tga/tga_artg.csv and updates the "Date Coverage by Dataset"
table in README.md with the current row counts and percentages.
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


def update_readme(readme_path, csv_path):
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
    match_rate_row = f"| TGA | {stats['total']:,} products (partial — ~{pct_of_artg:.0f}% of ARTG; scrape ongoing) | — | — |"
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

    if not csv_path.exists():
        print(f"Error: CSV file not found at {csv_path}", file=sys.stderr)
        sys.exit(1)

    if not readme_path.exists():
        print(f"Error: README.md not found at {readme_path}", file=sys.stderr)
        sys.exit(1)

    if update_readme(readme_path, csv_path):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
