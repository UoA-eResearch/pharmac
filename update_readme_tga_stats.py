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

    # Format the new table row
    new_row = (
        f"| TGA (`tga_artg.csv`) — partial scrape | "
        f"{stats['total']:,} products | "
        f"{stats['with_date']:,} ({stats['with_pct']:.1f}%) | "
        f"{stats['without_date']:,} ({stats['without_pct']:.1f}%) | "
        f"Registration dates are on individual ARTG product pages, not the listing page; full per-product scrape needed |"
    )

    # Read the README
    with open(readme_path, 'r') as f:
        content = f.read()

    # Pattern to match the TGA row in the "Date Coverage by Dataset" table
    # This matches the line that starts with "| TGA (`tga_artg.csv`)"
    pattern = r'\| TGA \(`tga_artg\.csv`\)[^\n]*\|[^\n]*\|[^\n]*\|[^\n]*\|[^\n]*\|'

    # Replace the row
    updated_content, num_subs = re.subn(pattern, new_row, content)

    if num_subs == 0:
        print("Error: Could not find TGA row in README.md to update", file=sys.stderr)
        return False

    if num_subs > 1:
        print(f"Warning: Found {num_subs} matches for TGA row, expected 1", file=sys.stderr)

    # Write the updated content back
    with open(readme_path, 'w') as f:
        f.write(updated_content)

    print(f"Updated README.md: {stats['total']:,} total rows, {stats['with_date']:,} ({stats['with_pct']:.1f}%) with dates")
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
