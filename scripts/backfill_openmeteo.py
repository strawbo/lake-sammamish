"""Backfill historical weather data from Open-Meteo archive API.

Fetches hourly historical weather (temperature, wind, solar, precipitation,
cloud cover) and air quality (AQI, PM2.5, UV index) data, then upserts
into met_data to fill gaps where King County buoy data is missing.

Open-Meteo archive has data back to 1959 for weather.
Air quality/UV data starts around August 2022.
"""

import os
import time
import requests
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("SUPABASE_DB_URL")

LAT = 47.5912
LON = -122.0906

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
AQI_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

# Date range for backfill
START_DATE = "2021-01-01"
END_DATE = "2025-12-31"

# AQI data starts around Aug 28, 2022
AQI_START_DATE = "2022-08-28"

# Chunk sizes (days) — smaller chunks to avoid timeouts
WEATHER_CHUNK_DAYS = 90
AQI_CHUNK_DAYS = 60

MAX_RETRIES = 3


def fetch_with_retry(url, params, retries=MAX_RETRIES):
    """Fetch URL with retry logic for timeouts."""
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=120)
            resp.raise_for_status()
            return resp.json()
        except (requests.Timeout, requests.ConnectionError) as e:
            if attempt < retries - 1:
                wait = (attempt + 1) * 5
                print(f"timeout, retrying in {wait}s...", end=" ", flush=True)
                time.sleep(wait)
            else:
                raise


def fetch_weather_chunk(start, end):
    """Fetch historical weather for a date range."""
    params = {
        "latitude": LAT,
        "longitude": LON,
        "start_date": start,
        "end_date": end,
        "hourly": ",".join([
            "temperature_2m",
            "apparent_temperature",
            "wind_speed_10m",
            "wind_direction_10m",
            "shortwave_radiation",
            "precipitation",
            "cloud_cover",
            "relative_humidity_2m",
        ]),
        "timezone": "America/Los_Angeles",
    }
    return fetch_with_retry(ARCHIVE_URL, params)


def fetch_aqi_chunk(start, end):
    """Fetch historical air quality for a date range."""
    params = {
        "latitude": LAT,
        "longitude": LON,
        "start_date": start,
        "end_date": end,
        "hourly": "us_aqi,pm2_5,uv_index",
        "timezone": "America/Los_Angeles",
    }
    return fetch_with_retry(AQI_URL, params)


if __name__ == "__main__":
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    print("Connected to database")

    # --- Backfill weather data into met_data ---
    start = datetime.strptime(START_DATE, "%Y-%m-%d")
    end_limit = datetime.strptime(END_DATE, "%Y-%m-%d")
    # Don't go past yesterday
    yesterday = datetime.now() - timedelta(days=1)
    if end_limit > yesterday:
        end_limit = yesterday

    total_weather = 0

    while start < end_limit:
        chunk_end = min(start + timedelta(days=WEATHER_CHUNK_DAYS - 1), end_limit)
        start_str = start.strftime("%Y-%m-%d")
        end_str = chunk_end.strftime("%Y-%m-%d")

        print(f"Fetching weather {start_str} to {end_str}...", end=" ", flush=True)
        try:
            data = fetch_weather_chunk(start_str, end_str)
            hourly = data["hourly"]

            batch = []
            for i, time_str in enumerate(hourly["time"]):
                dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M")
                temp_c = hourly["temperature_2m"][i]
                wind_kmh = hourly["wind_speed_10m"][i]
                solar_w = hourly["shortwave_radiation"][i]
                humidity = hourly["relative_humidity_2m"][i]

                # wind_speed_10m default unit is km/h, convert to m/s
                wind_ms_val = float(wind_kmh) / 3.6 if wind_kmh is not None else None

                batch.append((
                    dt,
                    float(humidity) if humidity is not None else None,
                    float(solar_w) if solar_w is not None else None,
                    None,  # pressure_mb (not fetched)
                    wind_ms_val,
                    float(hourly["wind_direction_10m"][i]) if hourly["wind_direction_10m"][i] is not None else None,
                    float(temp_c) if temp_c is not None else None,
                ))

            if batch:
                # Use COALESCE to not overwrite existing King County buoy data
                psycopg2.extras.execute_values(
                    cursor,
                    """
                    INSERT INTO met_data (date, relative_humidity, solar_radiation_w, pressure_mb,
                                          wind_speed_ms, wind_direction_deg, air_temperature_c)
                    VALUES %s
                    ON CONFLICT (date)
                    DO UPDATE SET
                        relative_humidity = COALESCE(met_data.relative_humidity, EXCLUDED.relative_humidity),
                        solar_radiation_w = COALESCE(met_data.solar_radiation_w, EXCLUDED.solar_radiation_w),
                        pressure_mb = COALESCE(met_data.pressure_mb, EXCLUDED.pressure_mb),
                        wind_speed_ms = COALESCE(met_data.wind_speed_ms, EXCLUDED.wind_speed_ms),
                        wind_direction_deg = COALESCE(met_data.wind_direction_deg, EXCLUDED.wind_direction_deg),
                        air_temperature_c = COALESCE(met_data.air_temperature_c, EXCLUDED.air_temperature_c);
                    """,
                    batch,
                    page_size=1000
                )
                conn.commit()
                total_weather += len(batch)
                print(f"{len(batch)} rows")
            else:
                print("no data")
        except Exception as e:
            print(f"ERROR: {e}")

        start = chunk_end + timedelta(days=1)
        time.sleep(2)  # Rate limit

    print(f"Weather backfill: {total_weather} total rows")

    # --- Backfill AQI + UV data ---
    # Store in weather_forecast table since met_data doesn't have AQI/UV columns
    # Use a fixed fetched_at to mark these as historical backfill
    backfill_marker = datetime(2000, 1, 1)  # Sentinel value for backfill data

    aqi_start = datetime.strptime(AQI_START_DATE, "%Y-%m-%d")
    total_aqi = 0

    while aqi_start < end_limit:
        chunk_end = min(aqi_start + timedelta(days=AQI_CHUNK_DAYS - 1), end_limit)
        start_str = aqi_start.strftime("%Y-%m-%d")
        end_str = chunk_end.strftime("%Y-%m-%d")

        print(f"Fetching AQI {start_str} to {end_str}...", end=" ", flush=True)
        try:
            data = fetch_aqi_chunk(start_str, end_str)
            hourly = data["hourly"]

            batch = []
            for i, time_str in enumerate(hourly["time"]):
                dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M")
                aqi = hourly["us_aqi"][i]
                uv = hourly["uv_index"][i]

                if aqi is None and uv is None:
                    continue

                batch.append((
                    dt,
                    backfill_marker,
                    None, None, None, None, None, None,
                    float(uv) if uv is not None else None,
                    None,
                    float(aqi) if aqi is not None else None,
                    None,
                ))

            if batch:
                psycopg2.extras.execute_values(
                    cursor,
                    """
                    INSERT INTO weather_forecast (
                        forecast_time, fetched_at,
                        temperature_f, feels_like_f, wind_speed_mph, wind_direction_deg,
                        precip_probability, cloud_cover, uv_index, solar_radiation_w,
                        us_aqi, pm25
                    ) VALUES %s
                    ON CONFLICT (forecast_time, fetched_at) DO NOTHING;
                    """,
                    batch,
                    page_size=1000
                )
                conn.commit()
                total_aqi += len(batch)
                print(f"{len(batch)} rows")
            else:
                print("no data")
        except Exception as e:
            print(f"ERROR: {e}")

        aqi_start = chunk_end + timedelta(days=1)
        time.sleep(2)

    print(f"AQI backfill: {total_aqi} total rows")

    cursor.close()
    conn.close()
    print("\nBackfill complete!")
