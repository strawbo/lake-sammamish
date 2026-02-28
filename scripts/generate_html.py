import os
import pandas as pd
import psycopg2
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DB_URL = os.getenv("SUPABASE_DB_URL")

# Connect to the database using SQLAlchemy
engine = create_engine(DB_URL)
conn = engine.connect()

# Define date range for the current year
current_date = pd.Timestamp.today()
start_date = current_date - pd.DateOffset(weeks=3)
end_date = current_date + pd.DateOffset(weeks=3)

# Query for current year
query_current = f"""
SELECT date, ROUND(CAST(MAX(temperature_c * 9/5 + 32) AS NUMERIC), 1) as max_temperature_f
FROM lake_data
WHERE date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'
AND depth_m < 1.5
GROUP BY date
ORDER BY date;
"""

# Define the current date and the 7-day window
start_date = current_date - pd.DateOffset(days=7)
end_date = current_date + pd.DateOffset(days=7)

# Query for past 5 years
query_past = f"""
SELECT date, EXTRACT(YEAR FROM date) as pYear,
       ROUND(CAST(MAX(temperature_c * 9/5 + 32) AS NUMERIC), 1) as max_temperature_f
FROM lake_data
WHERE EXTRACT(YEAR FROM date) BETWEEN EXTRACT(YEAR FROM CURRENT_DATE) - 5
                              AND EXTRACT(YEAR FROM CURRENT_DATE) - 1
    AND TO_CHAR(date, 'MM-DD') BETWEEN TO_CHAR(CAST('{start_date.strftime('%Y-%m-%d')}' AS DATE), 'MM-DD')
                                 AND TO_CHAR(CAST('{end_date.strftime('%Y-%m-%d')}' AS DATE), 'MM-DD')
    AND depth_m < 1.5
GROUP BY date, EXTRACT(YEAR FROM date)
ORDER BY date;
"""

# Query comfort scores for today + next 8 days (include all of today)
query_comfort = """
SELECT score_time, overall_score, label,
       water_temp_score, air_temp_score, wind_score, sun_score,
       rain_score, clarity_score, algae_score, aqi_score,
       override_reason, input_snapshot
FROM comfort_score
WHERE score_time >= DATE_TRUNC('day', NOW())
  AND score_time < DATE_TRUNC('day', NOW()) + INTERVAL '9 days'
ORDER BY score_time;
"""

# Query current conditions (latest comfort score)
query_current_comfort = """
SELECT score_time, overall_score, label,
       water_temp_score, air_temp_score, wind_score, sun_score,
       rain_score, clarity_score, algae_score, aqi_score,
       override_reason, input_snapshot
FROM comfort_score
ORDER BY ABS(EXTRACT(EPOCH FROM (score_time - NOW())))
LIMIT 1;
"""

# Query data freshness metadata
query_meta = """
SELECT
    (SELECT MAX(date) FROM lake_data WHERE depth_m < 1.5 AND temperature_c IS NOT NULL) AS latest_buoy,
    (SELECT MAX(computed_at) FROM comfort_score) AS latest_comfort,
    (SELECT MAX(fetched_at) FROM weather_forecast) AS latest_forecast,
    NOW() AS generated_at;
"""

# Load data into Pandas
df_meta = pd.read_sql(query_meta, conn)
df_current = pd.read_sql(query_current, conn)
df_past = pd.read_sql(query_past, conn)

# Comfort score data
df_comfort = pd.read_sql(query_comfort, conn)
df_current_comfort = pd.read_sql(query_current_comfort, conn)

# Close the database connection
conn.close()

# Convert dataframes to JSON
df_past.rename(columns={"pyear": "pYear"}, inplace=True)
df_past["pYear"] = df_past["pYear"].astype(int)
current_json = df_current.to_json(orient="records", date_format="iso")
past_json = df_past.to_json(orient="records", date_format="iso")

# Comfort data to JSON
comfort_json = df_comfort.to_json(orient="records", date_format="iso")
current_comfort_json = df_current_comfort.to_json(orient="records", date_format="iso")

# Meta data to JSON
meta_json = df_meta.to_json(orient="records", date_format="iso")

# Read the HTML template
with open("templates/template.html", "r", encoding="utf-8") as file:
    html_template = file.read()

# Inject JSON data
html_output = (
    html_template
    .replace("{{DATA_CURRENT}}", current_json)
    .replace("{{DATA_PAST}}", past_json)
    .replace("{{COMFORT_FORECAST}}", comfort_json)
    .replace("{{CURRENT_COMFORT}}", current_comfort_json)
    .replace("{{DATA_META}}", meta_json)
)

# Ensure output directory exists
output_path = "docs/index.html"
os.makedirs(os.path.dirname(output_path), exist_ok=True)

# Save the HTML file
with open(output_path, "w", encoding="utf-8") as file:
    file.write(html_output)

print(f"Successfully wrote {output_path}")
