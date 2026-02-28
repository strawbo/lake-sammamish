import csv
import psycopg2
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DB_URL = os.getenv("SUPABASE_DB_URL")

# Connect to Supabase
conn = psycopg2.connect(DB_URL)
cursor = conn.cursor()

print("Connected to the database")


def safe_float(value):
    """Convert a string to float, returning None for empty or invalid values."""
    if not value or not value.strip():
        return None
    try:
        return float(value)
    except ValueError:
        return None


# --- Import profile data ---
profile_inserted = 0
profile_updated = 0

if os.path.exists("SammamishProfile.txt"):
    with open("SammamishProfile.txt", "r") as file:
        csv_reader = csv.reader(file, delimiter="\t")
        headers = next(csv_reader, None)

        # Build column index map from headers
        # Expected columns: Date, Depth(m), Temperature(C), Dissolved Oxygen(mg/L),
        #   pH, Specific Conductance(µS), Chlorophyll(µg/L), Turbidity(NTU),
        #   Phycocyanin BGA(µg/L)
        col_idx = {}
        if headers:
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

        for row in csv_reader:
            if not row or row[0].strip().lower() == "date":
                continue

            try:
                date_time_obj = datetime.strptime(row[col_idx.get("date", 0)], "%m/%d/%Y %I:%M:%S %p")
            except (ValueError, IndexError):
                continue

            depth_m = safe_float(row[col_idx.get("depth", 1)])
            temperature_c = safe_float(row[col_idx.get("temp", 2)])
            turbidity_ntu = safe_float(row[col_idx.get("turbidity", 7)]) if "turbidity" in col_idx else None
            chlorophyll_ugl = safe_float(row[col_idx.get("chlorophyll", 6)]) if "chlorophyll" in col_idx else None
            phycocyanin_ugl = safe_float(row[col_idx.get("phycocyanin", 8)]) if "phycocyanin" in col_idx else None

            if temperature_c is not None:
                cursor.execute(
                    """
                    INSERT INTO lake_data (date, depth_m, temperature_c, turbidity_ntu, chlorophyll_ugl, phycocyanin_ugl)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (date, depth_m)
                    DO UPDATE SET temperature_c = EXCLUDED.temperature_c,
                                  turbidity_ntu = COALESCE(EXCLUDED.turbidity_ntu, lake_data.turbidity_ntu),
                                  chlorophyll_ugl = COALESCE(EXCLUDED.chlorophyll_ugl, lake_data.chlorophyll_ugl),
                                  phycocyanin_ugl = COALESCE(EXCLUDED.phycocyanin_ugl, lake_data.phycocyanin_ugl)
                    RETURNING xmax;
                    """,
                    (date_time_obj, depth_m, temperature_c, turbidity_ntu, chlorophyll_ugl, phycocyanin_ugl)
                )
                result = cursor.fetchone()
                if result and result[0] == 0:
                    profile_inserted += 1
                else:
                    profile_updated += 1

    print(f"Profile import: {profile_inserted} inserted, {profile_updated} updated.")
else:
    print("SammamishProfile.txt not found, skipping profile import.")


# --- Import meteorological data ---
met_inserted = 0
met_updated = 0

if os.path.exists("SammamishMet.txt"):
    with open("SammamishMet.txt", "r") as file:
        csv_reader = csv.reader(file, delimiter="\t")
        headers = next(csv_reader, None)

        # Build column index map from headers
        # Expected: Date, Relative Humidity(%), Solar Radiation(W/m²),
        #   Barometric Pressure(mb), Wind Speed(m/s), Wind Direction(°),
        #   Air Temperature(°C)
        col_idx = {}
        if headers:
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

        for row in csv_reader:
            if not row or row[0].strip().lower() == "date":
                continue

            try:
                date_time_obj = datetime.strptime(row[col_idx.get("date", 0)], "%m/%d/%Y %I:%M:%S %p")
            except (ValueError, IndexError):
                continue

            cursor.execute(
                """
                INSERT INTO met_data (date, relative_humidity, solar_radiation_w, pressure_mb,
                                      wind_speed_ms, wind_direction_deg, air_temperature_c)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (date)
                DO UPDATE SET relative_humidity = COALESCE(EXCLUDED.relative_humidity, met_data.relative_humidity),
                              solar_radiation_w = COALESCE(EXCLUDED.solar_radiation_w, met_data.solar_radiation_w),
                              pressure_mb = COALESCE(EXCLUDED.pressure_mb, met_data.pressure_mb),
                              wind_speed_ms = COALESCE(EXCLUDED.wind_speed_ms, met_data.wind_speed_ms),
                              wind_direction_deg = COALESCE(EXCLUDED.wind_direction_deg, met_data.wind_direction_deg),
                              air_temperature_c = COALESCE(EXCLUDED.air_temperature_c, met_data.air_temperature_c)
                RETURNING xmax;
                """,
                (
                    date_time_obj,
                    safe_float(row[col_idx.get("humidity", 1)]) if "humidity" in col_idx else None,
                    safe_float(row[col_idx.get("solar", 2)]) if "solar" in col_idx else None,
                    safe_float(row[col_idx.get("pressure", 3)]) if "pressure" in col_idx else None,
                    safe_float(row[col_idx.get("wind_speed", 4)]) if "wind_speed" in col_idx else None,
                    safe_float(row[col_idx.get("wind_dir", 5)]) if "wind_dir" in col_idx else None,
                    safe_float(row[col_idx.get("air_temp", 6)]) if "air_temp" in col_idx else None,
                )
            )
            result = cursor.fetchone()
            if result and result[0] == 0:
                met_inserted += 1
            else:
                met_updated += 1

    print(f"Met import: {met_inserted} inserted, {met_updated} updated.")
else:
    print("SammamishMet.txt not found, skipping met import.")


# Commit & close connections
conn.commit()
cursor.close()
conn.close()

print("Import complete.")

