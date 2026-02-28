"""Backfill missing months of Lake Sammamish data.

Fetches data for specified months from King County's DataScrape endpoint,
writes each month to SammamishProfile.txt, and imports into the database.

Usage:
    SUPABASE_DB_URL=... python scripts/backfill.py
"""

import csv
import os
import psycopg2
from datetime import datetime
from dotenv import load_dotenv
from download_data import fetch_month, write_tsv

load_dotenv()
DB_URL = os.getenv("SUPABASE_DB_URL")

# Months to backfill: October 2025 through February 2026
MONTHS_TO_BACKFILL = [
    (2025, 10),
    (2025, 11),
    (2025, 12),
    (2026, 1),
    (2026, 2),
]


def import_tsv(filepath, cursor):
    """Import a TSV file into the database. Returns (inserted, updated) counts."""
    inserted = 0
    updated = 0

    with open(filepath, "r") as f:
        reader = csv.reader(f, delimiter="\t")
        next(reader, None)  # skip header

        for row in reader:
            if not row or row[0].strip().lower() == "date":
                continue

            try:
                date_time_obj = datetime.strptime(row[0], "%m/%d/%Y %I:%M:%S %p")
            except ValueError:
                continue

            depth_m = float(row[1]) if row[1] else None

            try:
                temperature_c = float(row[2]) if row[2] else None
            except ValueError:
                continue

            if temperature_c is not None:
                cursor.execute(
                    """
                    INSERT INTO lake_data (date, depth_m, temperature_c)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (date, depth_m)
                    DO UPDATE SET temperature_c = EXCLUDED.temperature_c
                    RETURNING xmax;
                    """,
                    (date_time_obj, depth_m, temperature_c),
                )
                result = cursor.fetchone()
                if result and result[0] == 0:
                    inserted += 1
                else:
                    updated += 1

    return inserted, updated


if __name__ == "__main__":
    if not DB_URL:
        print("ERROR: SUPABASE_DB_URL not set")
        exit(1)

    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    print("Connected to database")

    total_inserted = 0
    total_updated = 0

    for year, month in MONTHS_TO_BACKFILL:
        print(f"\nFetching {year}-{month:02d}...")
        headers, rows = fetch_month(year, month)

        if not rows:
            print(f"  No data for {year}-{month:02d}")
            continue

        print(f"  Downloaded {len(rows)} rows")

        # Write temp file
        filepath = "SammamishProfile.txt"
        write_tsv(filepath, headers, rows)

        # Import
        inserted, updated = import_tsv(filepath, cursor)
        conn.commit()
        print(f"  Imported: {inserted} new, {updated} updated")

        total_inserted += inserted
        total_updated += updated

    cursor.close()
    conn.close()

    print(f"\nBackfill complete: {total_inserted} new rows, {total_updated} updated rows")
