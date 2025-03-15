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
SELECT DATE(date) as date, ROUND(CAST(MAX(temperature_c * 9/5 + 32) AS NUMERIC), 1) as max_temperature_f
FROM lake_data
WHERE date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'
AND depth_m < 1.5
GROUP BY DATE(date)
ORDER BY date;
"""

# Define the current date and the 7-day window
start_date = current_date - pd.DateOffset(days=7)
end_date = current_date + pd.DateOffset(days=7)

# Query for past 5 years
query_past = f"""
SELECT DATE(date) as date, EXTRACT(YEAR FROM date) as pYear, 
       ROUND(CAST(MAX(temperature_c * 9/5 + 32) AS NUMERIC), 1) as max_temperature_f
FROM lake_data
WHERE EXTRACT(YEAR FROM date) BETWEEN EXTRACT(YEAR FROM CURRENT_DATE) - 5 
                              AND EXTRACT(YEAR FROM CURRENT_DATE) - 1
    AND TO_CHAR(date, 'MM-DD') BETWEEN TO_CHAR(CAST('{start_date.strftime('%Y-%m-%d')}' AS DATE), 'MM-DD') 
                                 AND TO_CHAR(CAST('{end_date.strftime('%Y-%m-%d')}' AS DATE), 'MM-DD')
    AND depth_m < 1.5
GROUP BY DATE(date), EXTRACT(YEAR FROM date)
ORDER BY date;
"""

# Load data into Pandas
df_current = pd.read_sql(query_current, conn)
df_past = pd.read_sql(query_past, conn)

# Close the database connection
conn.close()

# Convert dataframes to JSON
df_past.rename(columns={"pyear": "pYear"}, inplace=True)
df_past["pYear"] = df_past["pYear"].astype(int)
current_json = df_current.to_json(orient="records", date_format="iso")
past_json = df_past.to_json(orient="records", date_format="iso")

# Read the HTML template
with open("templates/template.html", "r", encoding="utf-8") as file:
    html_template = file.read()

# Inject JSON data
html_output = html_template.replace("{{DATA_CURRENT}}", current_json).replace("{{DATA_PAST}}", past_json)

# Ensure output directory exists
output_path = "docs/index.html"
os.makedirs(os.path.dirname(output_path), exist_ok=True)

# Save the HTML file
with open(output_path, "w", encoding="utf-8") as file:
    file.write(html_output)

print(f"✅ Successfully wrote {output_path}")
