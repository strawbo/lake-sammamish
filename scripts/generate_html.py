import psycopg2
import os
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DB_URL = os.getenv("SUPABASE_DB_URL")

# Connect to Supabase
conn = psycopg2.connect(DB_URL)
cursor = conn.cursor()

# Set date range (previous 3 weeks & next 3 weeks from today)
today = datetime.today()
start_date = today - timedelta(weeks=3)
end_date = today + timedelta(weeks=3)

# Query for the last 6 weeks of data (current year)
query_current = f"""
SELECT DATE(date) as date, ROUND(CAST(MAX(temperature_c * 9/5 + 32) AS NUMERIC), 1) as max_temperature_f
FROM lake_data
WHERE date BETWEEN '2025-02-22' AND '2025-04-05'
AND depth_m < 1.5
GROUP BY DATE(date)
ORDER BY date;
"""

# Query for the same date range in the past 5 years
query_past = f"""
SELECT DATE(date) as date, EXTRACT(YEAR FROM date) as pYear, 
       ROUND(CAST(MAX(temperature_c * 9/5 + 32) AS NUMERIC), 1) as max_temperature_f
FROM lake_data
WHERE 
    EXTRACT(YEAR FROM date) BETWEEN EXTRACT(YEAR FROM CURRENT_DATE) - 5 
                                AND EXTRACT(YEAR FROM CURRENT_DATE) - 1
    AND TO_CHAR(date, 'MM-DD') BETWEEN TO_CHAR('2025-02-22'::DATE, 'MM-DD') 
                                   AND TO_CHAR('2025-04-05'::DATE, 'MM-DD')
    AND depth_m < 1.5
GROUP BY DATE(date), EXTRACT(YEAR FROM date)
ORDER BY date;
"""

# Execute queries
df_current = pd.read_sql(query_current, conn)
df_past = pd.read_sql(query_past, conn)

# Close the connection
cursor.close()
conn.close()

# Convert data to JSON format for JavaScript
current_json = df_current.to_json(orient="records", date_format="iso")
past_json = df_past.to_json(orient="records", date_format="iso")

# Generate HTML file for GitHub Pages
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
        const ctx = document.getElementById("lakeChart").getContext("2d");

        // Current Year Data
        const dataCurrent = {current_json};

        // Past 5 Years Data
        const dataPast = {past_json};

        const datasets = [
            {{
                label: "Current Year",
                data: dataCurrent.map(row => ({{
                    x: new Date(row.date),
                    y: row.max_temperature_f
                }})),
                borderColor: "rgba(75, 192, 192, 1)",
                backgroundColor: "rgba(75, 192, 192, 0.2)",
                fill: false,
                borderWidth: 5,
                tension: 0.1
            }}
        ];

        const colors = ["rgba(192, 75, 75, 1)", "rgba(192, 192, 75, 1)", "rgba(75, 75, 192, 1)", "rgba(192, 75, 192, 1)", "rgba(75, 192, 75, 1)"];
        let colorIndex = 0;

        const years = [...new Set(dataPast.map(row => row.pYear))];

        years.forEach(year => {{
            const filteredData = dataPast.filter(item => item.pYear === year);
            datasets.push({{
                label: `Year ${year}`,
                data: filteredData.map(row => ({{
                    x: new Date(row.date.replace(/^\\d{{4}}-/, new Date().getFullYear() + '-')), 
                    y: row.max_temperature_f
                }})),
                borderColor: colors[colorIndex % colors.length],
                borderWidth: 2,
                borderDash: [5, 5],
                fill: false,
                tension: 0.1
            }});
            colorIndex++;
        }});

        new Chart(ctx, {{
            type: "line",
            data: {{ datasets }},
            options: {{
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
                        beginAtZero: false,
                        suggestedMin: 50,
                        suggestedMax: 90,
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

# Save to GitHub Pages directory
output_path = "../lake-sammamish.github.io/index.html"
with open(output_path, "w", encoding="utf-8") as file:
    file.write(html_content)

print("HTML file generated successfully at:", output_path)
