"""Export comfort score data as standalone JSON for the iOS app.

Outputs docs/comfort-data.json with the same data that generate_html.py
injects into the HTML template, but as a standalone JSON file.
"""

import json
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()
DB_URL = os.getenv("SUPABASE_DB_URL")

engine = create_engine(DB_URL)
conn = engine.connect()

# Comfort forecast: yesterday through +8 days
df_forecast = pd.read_sql("""
SELECT score_time, overall_score, label,
       water_temp_score, air_temp_score, wind_score, sun_score,
       rain_score, clarity_score, algae_score, aqi_score,
       override_reason, input_snapshot
FROM comfort_score
WHERE score_time >= DATE_TRUNC('day', NOW()) - INTERVAL '1 day'
  AND score_time < DATE_TRUNC('day', NOW()) + INTERVAL '9 days'
ORDER BY score_time;
""", conn)

# Current comfort: closest entry to now
df_current = pd.read_sql("""
SELECT score_time, overall_score, label,
       water_temp_score, air_temp_score, wind_score, sun_score,
       rain_score, clarity_score, algae_score, aqi_score,
       override_reason, input_snapshot
FROM comfort_score
ORDER BY ABS(EXTRACT(EPOCH FROM (score_time - NOW())))
LIMIT 1;
""", conn)

# Data freshness metadata
df_meta = pd.read_sql("""
SELECT
    TO_CHAR((SELECT MAX(date) FROM lake_data WHERE depth_m < 1.5 AND temperature_c IS NOT NULL)
            AT TIME ZONE 'America/Los_Angeles', 'YYYY-MM-DD"T"HH24:MI:SS') AS latest_buoy,
    TO_CHAR(NOW() AT TIME ZONE 'America/Los_Angeles', 'YYYY-MM-DD"T"HH24:MI:SS') AS generated_at;
""", conn)

# Historical weather averages (±7 DOY window)
df_hist = pd.read_sql("""
SELECT
    ROUND(CAST(AVG(max_air_c) * 9.0/5.0 + 32 AS NUMERIC), 1) AS avg_feels_like_f,
    ROUND(CAST(AVG(avg_wind_ms) * 2.237 AS NUMERIC), 1) AS avg_wind_mph,
    ROUND(CAST(AVG(max_solar_w) AS NUMERIC), 0) AS avg_solar_w,
    ROUND(CAST(AVG(total_precip_mm) * 15 AS NUMERIC), 0) AS avg_rain_pct,
    ROUND(CAST(AVG(avg_aqi) AS NUMERIC), 0) AS avg_aqi
FROM (
    SELECT date::date AS day,
           MAX(air_temperature_c) AS max_air_c,
           AVG(wind_speed_ms) AS avg_wind_ms,
           MAX(solar_radiation_w) AS max_solar_w,
           SUM(precipitation_mm) AS total_precip_mm,
           AVG(us_aqi) AS avg_aqi
    FROM met_data
    WHERE air_temperature_c IS NOT NULL
      AND EXTRACT(YEAR FROM date) < EXTRACT(YEAR FROM NOW())
      AND ABS(EXTRACT(DOY FROM date) - EXTRACT(DOY FROM NOW())) <= 7
    GROUP BY date::date
) daily;
""", conn)

conn.close()


def df_to_records(df):
    """Convert DataFrame to list of dicts with ISO date strings."""
    records = json.loads(df.to_json(orient="records", date_format="iso"))
    return records


forecast_records = df_to_records(df_forecast)
current_records = df_to_records(df_current)
meta_records = df_to_records(df_meta)
hist_records = df_to_records(df_hist)

output = {
    "generated_at": meta_records[0]["generated_at"] if meta_records else None,
    "current": current_records[0] if current_records else None,
    "forecast": forecast_records,
    "meta": meta_records[0] if meta_records else {},
    "hist_weather": hist_records[0] if hist_records else {},
}

output_path = "docs/comfort-data.json"
os.makedirs(os.path.dirname(output_path), exist_ok=True)

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, separators=(",", ":"))

print(f"Successfully wrote {output_path} ({len(forecast_records)} forecast entries)")
