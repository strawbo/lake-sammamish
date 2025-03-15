import os
import pandas as pd
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables (Supabase DB URL)
load_dotenv()
DB_URL = os.getenv("SUPABASE_DB_URL")

# Connect to PostgreSQL Database
conn = psycopg2.connect(DB_URL)
cursor = conn.cursor()

# Define date range (Last 3 weeks + Next 3 weeks for previous years)
today = datetime.today()
start_date = today - timedelta(weeks=3)
end_date = today + timedelta(weeks=3)

# Query for current year's data (depth < 1.5m)
query_current = f"""
SELECT DATE(date) as date, ROUND(CAST(MAX(temperature_c * 9/5 + 32) AS NUMERIC), 1) as max_temperature_f
FROM lake_data
WHERE date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'
AND depth_m < 1.5
GROUP BY DATE(date)
ORDER BY date;
"""

# Query for past 5 years' data (same date range but previous years)
query_past = f"""
SELECT DATE(date) as date, EXTRACT(YEAR FROM date) as pYear, 
       ROUND(CAST(MAX(temperature_c * 9/5 + 32) AS NUMERIC), 1) as max_temperature_f
FROM lake_data
WHERE 
    EXTRACT(YEAR FROM date) BETWEEN EXTRACT(YEAR FROM CURRENT_DATE) - 5 
                              AND EXTRACT(YEAR FROM CURRENT_DATE) - 1
    AND TO_CHAR(date, 'MM-DD') BETWEEN TO_CHAR('{start_date.strftime('%Y-%m-%d')}'::DATE, 'MM-DD') 
                                 AND TO_CHAR('{end_date.strftime('%Y-%m-%d')}'::DATE, 'MM-DD')
AND depth_m < 1.5
GROUP BY DATE(date), EXTRACT(YEAR FROM date)
ORDER BY date;
"""

# Fetch data
df_current = pd.read_sql(query_current, conn)
df_past = pd.read_sql(query_past, conn)

# Close the database connection
cursor.close()
conn.close()

# Convert DataFrames to JSON for Chart.js
data_current_json = df_current.to_json(orient="records", date_format="iso")
data_past_json = df_past.to_json(orient="records", date_format="iso")

# Initialize HTML content
html_content = f"""
<!DOCTYPE html>
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
        const ctx = document.getElementById("lakeChart").getContext("2d");

        // Data for current year (Thicker Line)
        const dataCurrent = {data_current_json};

        // Data for past 5 years
        const dataPast = {data_past_json};

        // Format datasets for Chart.js
        const datasets = [
            {{
                label: "Current Year",
                data: dataCurrent.map(row => {{ x: new Date(row.date), y: row.max_temperature_f }}),
                borderColor: "rgba(75, 192, 192, 1)",
                backgroundColor: "rgba(75, 192, 192, 0.2)",
                borderWidth: 5,  // Thicker line for the current year
                tension: 0.1
            }}
        ];

        // Color palette for past years
        const colors = ["rgba(192, 75, 75, 1)", "rgba(192, 192, 75, 1)", "rgba(75, 75, 192, 1)", "rgba(192, 75, 192, 1)", "rgba(75, 192, 75, 1)"];
        let colorIndex = 0;

        // Process past 5 years' data
        const years = Array.from(new Set(dataPast.map(row => row.pYear)));

        years.forEach(jYear => {{
            const filteredData = dataPast.filter(item => item.pYear === jYear);
            datasets.push({{
                label: `Year ${jYear}`,
                data: filteredData.map(row => {{ x: new Date(row.date), y: row.max_temperature_f }}),
                borderColor: colors[colorIndex % colors.length],
                borderWidth: 2,
                borderDash: [5, 5],  // Dashed line for past years
                tension: 0.1
            }});
            colorIndex++;
        }});

        // Create Chart.js line chart
        const lakeChart = new Chart(ctx, {{
            type: "line",
            data: {{ datasets }},
            options: {{
                responsive: true,
                scales: {{
                    x: {{
                        type: "time",
                        time: {{
                            unit: "day",
                            tooltipFormat: 'MMM d',
                            displayFormats: {{
                                day: 'MMM d'
                            }}
                        }},
                        title: {{
                            display: true,
                            text: 'Date'
                        }}
                    }},
                    y: {{
                        suggestedMin: 50, // Start Y-axis at 50°F
                        suggestedMax: 90, // End Y-axis at 90°F
                        title: {{
                            display: true,
                            text: 'Temperature (°F)'
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""

# Save HTML to file (GitHub Pages path)
output_path = "../lake-sammamish/index.html"
with open(output_path, "w") as file:
    file.write(html_content)

print(f"HTML file successfully generated at {output_path}")
