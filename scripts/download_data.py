"""Download Lake Sammamish profile data from King County's lake buoy site.

Uses the DataScrape.aspx GET endpoint which returns an HTML table.
Parses the table and writes a tab-delimited file (SammamishProfile.txt)
compatible with import_data.py.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime

# King County lake buoy data endpoint (simple GET, no ASP.NET postback needed)
BASE_URL = "https://green2.kingcounty.gov/lake-buoy/DataScrape.aspx"

# Use current month and year
now = datetime.now()
current_year = str(now.year)
current_month = str(now.month)


def fetch_month(year, month):
    """Fetch profile data for a single month. Returns list of rows (list of strings)."""
    params = {
        "type": "profile",
        "buoy": "sammamish",
        "year": str(year),
        "month": str(month),
    }
    resp = requests.get(BASE_URL, params=params)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table")
    if not table:
        print(f"  No data table found for {year}-{month:02d}")
        return [], []

    # Extract headers
    headers = [th.get_text(strip=True) for th in table.find_all("th")]

    # Extract data rows
    rows = []
    for tr in table.find_all("tr")[1:]:  # skip header row
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
    print(f"Fetching Lake Sammamish profile data for {current_year}-{int(current_month):02d}...")
    headers, rows = fetch_month(current_year, current_month)

    if rows:
        output_path = "SammamishProfile.txt"
        write_tsv(output_path, headers, rows)
        print(f"Data downloaded and saved as {output_path} successfully.")
        print(f"  {len(rows)} data rows")
    else:
        print("No data available for the current month.")
