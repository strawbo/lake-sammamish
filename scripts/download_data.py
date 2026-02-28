"""Download Lake Sammamish profile and meteorological data from King County.

Uses the DataScrape.aspx GET endpoint which returns HTML tables.
Parses the tables and writes tab-delimited files compatible with import_data.py.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime

BASE_URL = "https://green2.kingcounty.gov/lake-buoy/DataScrape.aspx"

now = datetime.now()
current_year = str(now.year)
current_month = str(now.month)


def fetch_month(year, month, data_type="profile"):
    """Fetch data for a single month. Returns (headers, rows)."""
    params = {
        "type": data_type,
        "buoy": "sammamish",
        "year": str(year),
        "month": str(month),
    }
    resp = requests.get(BASE_URL, params=params)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table")
    if not table:
        print(f"  No data table found for {data_type} {year}-{month:02d}")
        return [], []

    headers = [th.get_text(strip=True) for th in table.find_all("th")]

    rows = []
    for tr in table.find_all("tr")[1:]:
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if cells and len(cells) == len(headers):
            rows.append(cells)

    return headers, rows


def write_tsv(filepath, headers, all_rows):
    """Write headers and rows as a tab-delimited file."""
    with open(filepath, "w") as f:
        f.write("\t".join(headers) + "\n")
        for row in all_rows:
            f.write("\t".join(row) + "\n")


if __name__ == "__main__":
    # Download profile data
    print(f"Fetching profile data for {current_year}-{int(current_month):02d}...")
    headers, rows = fetch_month(current_year, current_month, "profile")
    if rows:
        write_tsv("SammamishProfile.txt", headers, rows)
        print(f"  Saved SammamishProfile.txt ({len(rows)} rows)")
    else:
        print("  No profile data available.")

    # Download meteorological data
    print(f"Fetching met data for {current_year}-{int(current_month):02d}...")
    headers, rows = fetch_month(current_year, current_month, "met")
    if rows:
        write_tsv("SammamishMet.txt", headers, rows)
        print(f"  Saved SammamishMet.txt ({len(rows)} rows)")
    else:
        print("  No met data available.")
