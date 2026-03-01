"""Backfill historical King County buoy data (profile + met).

Fetches data month by month for the specified year range from the
King County DataScrape endpoint, then upserts into lake_data and met_data.
"""

import os
import time
import requests
import psycopg2
import psycopg2.extras
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("SUPABASE_DB_URL")

BASE_URL = "https://green2.kingcounty.gov/lake-buoy/DataScrape.aspx"

# Years to backfill
START_YEAR = 2021
END_YEAR = 2026


def safe_float(value):
    if not value or not value.strip():
        return None
    try:
        return float(value)
    except ValueError:
        return None


def fetch_month(year, month, data_type="profile"):
    """Fetch data for a single month. Returns (headers, rows)."""
    params = {
        "type": data_type,
        "buoy": "sammamish",
        "year": str(year),
        "month": str(month),
    }
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table")
    if not table:
        return [], []

    headers = [th.get_text(strip=True) for th in table.find_all("th")]
    rows = []
    for tr in table.find_all("tr")[1:]:
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if cells and len(cells) == len(headers):
            rows.append(cells)
    return headers, rows


def parse_profile_rows(headers, rows):
    """Parse profile rows into tuples for lake_data upsert."""
    col_idx = {}
    for i, h in enumerate(headers):
        hl = h.strip().lower()
        if "date" in hl:
            col_idx["date"] = i
        elif "depth" in hl:
            col_idx["depth"] = i
        elif "temperature" in hl:
            col_idx["temp"] = i
        elif "turbidity" in hl:
            col_idx["turbidity"] = i
        elif "chlorophyll" in hl:
            col_idx["chlorophyll"] = i
        elif "phycocyanin" in hl:
            col_idx["phycocyanin"] = i

    batch = []
    for row in rows:
        try:
            dt = datetime.strptime(row[col_idx.get("date", 0)], "%m/%d/%Y %I:%M:%S %p")
        except (ValueError, IndexError):
            continue

        temp_c = safe_float(row[col_idx.get("temp", 2)])
        if temp_c is None:
            continue

        batch.append((
            dt,
            safe_float(row[col_idx.get("depth", 1)]),
            temp_c,
            safe_float(row[col_idx.get("turbidity", -1)]) if "turbidity" in col_idx else None,
            safe_float(row[col_idx.get("chlorophyll", -1)]) if "chlorophyll" in col_idx else None,
            safe_float(row[col_idx.get("phycocyanin", -1)]) if "phycocyanin" in col_idx else None,
        ))
    return batch


def parse_met_rows(headers, rows):
    """Parse met rows into tuples for met_data upsert."""
    col_idx = {}
    for i, h in enumerate(headers):
        hl = h.strip().lower()
        if "date" in hl:
            col_idx["date"] = i
        elif "humidity" in hl:
            col_idx["humidity"] = i
        elif "solar" in hl or "radiation" in hl:
            col_idx["solar"] = i
        elif "pressure" in hl or "barometric" in hl:
            col_idx["pressure"] = i
        elif "wind speed" in hl or "wind_speed" in hl:
            col_idx["wind_speed"] = i
        elif "wind dir" in hl or "wind_dir" in hl:
            col_idx["wind_dir"] = i
        elif "air temp" in hl or "air_temp" in hl:
            col_idx["air_temp"] = i

    batch = []
    for row in rows:
        try:
            dt = datetime.strptime(row[col_idx.get("date", 0)], "%m/%d/%Y %I:%M:%S %p")
        except (ValueError, IndexError):
            continue

        batch.append((
            dt,
            safe_float(row[col_idx.get("humidity", -1)]) if "humidity" in col_idx else None,
            safe_float(row[col_idx.get("solar", -1)]) if "solar" in col_idx else None,
            safe_float(row[col_idx.get("pressure", -1)]) if "pressure" in col_idx else None,
            safe_float(row[col_idx.get("wind_speed", -1)]) if "wind_speed" in col_idx else None,
            safe_float(row[col_idx.get("wind_dir", -1)]) if "wind_dir" in col_idx else None,
            safe_float(row[col_idx.get("air_temp", -1)]) if "air_temp" in col_idx else None,
        ))
    return batch


if __name__ == "__main__":
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    print("Connected to database")

    total_profile = 0
    total_met = 0

    for year in range(START_YEAR, END_YEAR + 1):
        for month in range(1, 13):
            # Skip future months
            if year == datetime.now().year and month > datetime.now().month:
                break

            # Profile data
            print(f"Fetching profile {year}-{month:02d}...", end=" ", flush=True)
            try:
                headers, rows = fetch_month(year, month, "profile")
                if rows:
                    batch = parse_profile_rows(headers, rows)
                    if batch:
                        psycopg2.extras.execute_values(
                            cursor,
                            """
                            INSERT INTO lake_data (date, depth_m, temperature_c, turbidity_ntu, chlorophyll_ugl, phycocyanin_ugl)
                            VALUES %s
                            ON CONFLICT (date, depth_m)
                            DO UPDATE SET temperature_c = EXCLUDED.temperature_c,
                                          turbidity_ntu = COALESCE(EXCLUDED.turbidity_ntu, lake_data.turbidity_ntu),
                                          chlorophyll_ugl = COALESCE(EXCLUDED.chlorophyll_ugl, lake_data.chlorophyll_ugl),
                                          phycocyanin_ugl = COALESCE(EXCLUDED.phycocyanin_ugl, lake_data.phycocyanin_ugl);
                            """,
                            batch,
                            page_size=500
                        )
                        total_profile += len(batch)
                    print(f"{len(batch)} rows")
                else:
                    print("no data")
            except Exception as e:
                print(f"ERROR: {e}")

            # Met data
            print(f"Fetching met {year}-{month:02d}...", end=" ", flush=True)
            try:
                headers, rows = fetch_month(year, month, "met")
                if rows:
                    batch = parse_met_rows(headers, rows)
                    if batch:
                        psycopg2.extras.execute_values(
                            cursor,
                            """
                            INSERT INTO met_data (date, relative_humidity, solar_radiation_w, pressure_mb,
                                                  wind_speed_ms, wind_direction_deg, air_temperature_c)
                            VALUES %s
                            ON CONFLICT (date)
                            DO UPDATE SET relative_humidity = COALESCE(EXCLUDED.relative_humidity, met_data.relative_humidity),
                                          solar_radiation_w = COALESCE(EXCLUDED.solar_radiation_w, met_data.solar_radiation_w),
                                          pressure_mb = COALESCE(EXCLUDED.pressure_mb, met_data.pressure_mb),
                                          wind_speed_ms = COALESCE(EXCLUDED.wind_speed_ms, met_data.wind_speed_ms),
                                          wind_direction_deg = COALESCE(EXCLUDED.wind_direction_deg, met_data.wind_direction_deg),
                                          air_temperature_c = COALESCE(EXCLUDED.air_temperature_c, met_data.air_temperature_c);
                            """,
                            batch,
                            page_size=500
                        )
                        total_met += len(batch)
                    print(f"{len(batch)} rows")
                else:
                    print("no data")
            except Exception as e:
                print(f"ERROR: {e}")

            conn.commit()
            time.sleep(0.5)  # Be polite to the King County server

    cursor.close()
    conn.close()
    print(f"\nBackfill complete: {total_profile} profile rows, {total_met} met rows")
