"""Fetch 7-day weather and air quality forecasts from Open-Meteo."""

import os
import requests
import psycopg2
import psycopg2.extras
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("SUPABASE_DB_URL")

# Lake Sammamish coordinates
LAT = 47.5912
LON = -122.0906

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
AQI_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


def fetch_weather():
    """Fetch hourly weather forecast for next 8 days."""
    params = {
        "latitude": LAT,
        "longitude": LON,
        "hourly": ",".join([
            "temperature_2m",
            "apparent_temperature",
            "wind_speed_10m",
            "wind_direction_10m",
            "precipitation_probability",
            "cloud_cover",
            "uv_index",
            "shortwave_radiation",
        ]),
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "timezone": "America/Los_Angeles",
        "forecast_days": 8,
    }
    resp = requests.get(WEATHER_URL, params=params)
    resp.raise_for_status()
    return resp.json()


def fetch_aqi():
    """Fetch hourly air quality forecast for next 7 days."""
    params = {
        "latitude": LAT,
        "longitude": LON,
        "hourly": "us_aqi,pm2_5",
        "timezone": "America/Los_Angeles",
        "forecast_days": 7,
    }
    resp = requests.get(AQI_URL, params=params)
    resp.raise_for_status()
    return resp.json()


def merge_and_upsert(weather_data, aqi_data):
    """Merge weather and AQI data, upsert into weather_forecast table."""
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()

    w_hourly = weather_data["hourly"]
    a_hourly = aqi_data["hourly"]

    # Build AQI lookup by timestamp
    aqi_lookup = {}
    for i, t in enumerate(a_hourly["time"]):
        aqi_lookup[t] = {
            "us_aqi": a_hourly["us_aqi"][i],
            "pm25": a_hourly["pm2_5"][i],
        }

    fetched_at = datetime.now()
    batch = []

    for i, time_str in enumerate(w_hourly["time"]):
        forecast_time = datetime.strptime(time_str, "%Y-%m-%dT%H:%M")
        aqi = aqi_lookup.get(time_str, {})

        batch.append((
            forecast_time, fetched_at,
            w_hourly["temperature_2m"][i],
            w_hourly["apparent_temperature"][i],
            w_hourly["wind_speed_10m"][i],
            w_hourly["wind_direction_10m"][i],
            w_hourly["precipitation_probability"][i],
            w_hourly["cloud_cover"][i],
            w_hourly["uv_index"][i],
            w_hourly["shortwave_radiation"][i],
            aqi.get("us_aqi"),
            aqi.get("pm25"),
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
            page_size=200
        )

    conn.commit()
    cursor.close()
    conn.close()
    return len(batch)


if __name__ == "__main__":
    print("Fetching weather forecast...")
    weather = fetch_weather()
    print(f"  Got {len(weather['hourly']['time'])} hourly weather records")

    print("Fetching air quality forecast...")
    aqi = fetch_aqi()
    print(f"  Got {len(aqi['hourly']['time'])} hourly AQI records")

    count = merge_and_upsert(weather, aqi)
    print(f"  Upserted {count} forecast rows.")
