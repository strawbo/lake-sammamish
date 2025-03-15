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

# Define date range
current_date = pd.Timestamp.today()
start_date = current_date - pd.DateOffset(weeks=3)  # 3 weeks before today
end_date = current_date + pd.DateOffset(weeks=3)  # 3 weeks after today

# Query for current year (last 6 weeks)
query_current = f"""
SELECT DATE(date) as date, ROUND(CAST(MAX(temperature_c * 9/5 + 32) AS NUMERIC), 1) as max_temperature_f
FROM lake_data
WHERE date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'
AND depth_m < 1.5
GROUP BY DATE(date)
ORDER BY date;
"""

# Query for past 5 years (same date range, previous years)
query_past = f"""
SELECT DATE(date) as date, EXTRACT(YEAR FROM date) as pYear, 
       ROUND(CAST(MAX(temperature_c * 9/5 + 32) AS NUMERIC), 1) as max_temperature_f
FROM lake_data
WHERE 
    EXTRACT(YEAR FROM date) BETWEEN EXTRACT(YEAR FROM CURRENT_DATE) - 5 
                              AND EXTRACT(YEAR FROM CURRENT_DATE) - 1
    AND TO_CHAR(date, 'MM-DD') BETWEEN TO_CHAR(CAST('2025-02-22' AS DATE), 'MM-DD') 
                                 AND TO_CHAR(CAST('2025-04-05' AS DATE), 'MM-DD')
    AND depth_m < 1.5
GROUP BY DATE(date), EXTRACT(YEAR FROM date)
ORDER BY date;
"""

# Load data into Pandas
df_current = pd.read_sql(query_current, conn)
df_past = pd.read_sql(query_past, conn)

# Close the database connection
conn.close()

# Convert dataframes to JSON format for JavaScript
current_json = df_current.to_json(orient="records", date_format="iso")
past_json = df_past.to_json(orient="records", date_format="iso")

# Extract unique years for labeling
print(df_past.head())  # Debugging step: Check what columns exist
years = df_past["pYear"].unique()

# Generate the JavaScript dataset definitions
datasets_js = """
const datasets = [
    {
        label: "Current Year",
        data: dataCurrent.map(row => ({ x: row.date, y: row.max_temperature_f })),
        borderColor: "rgba(75, 192, 192, 1)",
        backgroundColor: "rgba(75, 192, 192, 0.2)",
        fill: false,
        borderWidth: 5,
        tension: 0.1
    },"""

# Define colors for previous years
colors = ["rgba(192, 75, 75, 1)", "rgba(192, 192, 75, 1)", "rgba(75, 75, 192, 1)", "rgba(192, 75, 192, 1)", "rgba(75, 192, 75, 1)"]

for i, year in enumerate(years):
    datasets_js += f"""
    {{
        label: "Year {year}",
        data: dataPast.filter(row => row.pYear === {year}).map(row => ({{
            x: row.date,
            y: row.max_temperature_f
        }})),
        borderColor: "{colors[i % len(colors)]}",
        borderDash: [5, 5],
        tension: 0.1
    }},"""

datasets_js = datasets_js.rstrip(",") + "\n];"  # Remove last comma

# Generate HTML content
html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Lake Sammamish Water Temperature</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns"></script>
</head>
<body>
    <h1>Lake Sammamish Water Temperature</h1>
    <canvas id="lakeChart" width="400" height="200"></canvas>
    <script>
        const dataCurrent = {current_json};
        const dataPast = {past_json};

        {datasets_js}

        const ctx = document.getElementById("lakeChart").getContext("2d");

        new Chart(ctx, {{
            type: "line",
            data: {{
                datasets: datasets
            }},
            options: {{
                scales: {{
                    x: {{
                        type: "time",
                        time: {{
                            unit: "day",
                            tooltipFormat: "MMM d",
                            displayFormats: {{
                                day: "MMM d"
                            }}
                        }},
                        title: {{
                            display: true,
                            text: "Date"
                        }}
                    }},
                    y: {{
                        suggestedMin: 50,
                        suggestedMax: 90,
                        title: {{
                            display: true,
                            text: "Temperature (°F)"
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""

# Save the HTML file
output_path = "../lake-sammamish/index.html"
with open(output_path, "w") as file:
    file.write(html_content)

print(f"HTML file successfully created at {output_path}")
