"""Database migration: add tables and columns for swimming comfort score."""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("SUPABASE_DB_URL")

MIGRATIONS = [
    # Add water quality columns to existing lake_data table
    """
    ALTER TABLE lake_data
    ADD COLUMN IF NOT EXISTS turbidity_ntu NUMERIC,
    ADD COLUMN IF NOT EXISTS chlorophyll_ugl NUMERIC,
    ADD COLUMN IF NOT EXISTS phycocyanin_ugl NUMERIC;
    """,

    # Meteorological observations from the buoy (15-min intervals)
    """
    CREATE TABLE IF NOT EXISTS met_data (
        date              TIMESTAMP NOT NULL PRIMARY KEY,
        relative_humidity NUMERIC,
        solar_radiation_w NUMERIC,
        pressure_mb       NUMERIC,
        wind_speed_ms     NUMERIC,
        wind_direction_deg NUMERIC,
        air_temperature_c NUMERIC
    );
    """,

    # Open-Meteo weather + air quality forecasts (hourly)
    """
    CREATE TABLE IF NOT EXISTS weather_forecast (
        forecast_time      TIMESTAMP NOT NULL,
        fetched_at         TIMESTAMP NOT NULL DEFAULT NOW(),
        temperature_f      NUMERIC,
        feels_like_f       NUMERIC,
        wind_speed_mph     NUMERIC,
        wind_direction_deg NUMERIC,
        precip_probability NUMERIC,
        cloud_cover        NUMERIC,
        uv_index           NUMERIC,
        solar_radiation_w  NUMERIC,
        us_aqi             NUMERIC,
        pm25               NUMERIC,
        PRIMARY KEY (forecast_time, fetched_at)
    );
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_weather_forecast_latest
    ON weather_forecast (forecast_time, fetched_at DESC);
    """,

    # Pre-computed comfort scores (hourly)
    """
    CREATE TABLE IF NOT EXISTS comfort_score (
        score_time       TIMESTAMP NOT NULL PRIMARY KEY,
        computed_at      TIMESTAMP NOT NULL DEFAULT NOW(),
        overall_score    NUMERIC NOT NULL,
        label            TEXT NOT NULL,
        water_temp_score NUMERIC,
        air_temp_score   NUMERIC,
        wind_score       NUMERIC,
        sun_score        NUMERIC,
        rain_score       NUMERIC,
        clarity_score    NUMERIC,
        algae_score      NUMERIC,
        aqi_score        NUMERIC,
        override_reason  TEXT,
        input_snapshot   JSONB
    );
    """,
]

if __name__ == "__main__":
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    print("Connected to database")

    for i, sql in enumerate(MIGRATIONS, 1):
        print(f"Running migration {i}/{len(MIGRATIONS)}...")
        cursor.execute(sql)

    conn.commit()
    cursor.close()
    conn.close()
    print("All migrations complete.")
