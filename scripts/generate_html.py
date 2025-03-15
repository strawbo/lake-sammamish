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

# Define the current date and the 7-day window around it
current_date = pd.Timestamp.today()
start_date = current_date - pd.DateOffset(days=7)  # 7 days before today
end_date = current_date + pd.DateOffset(days=7)    # 7 days after today

# Query for past 5 years (same date range, previous years)
query_past = f"""
SELECT DATE(date) as date, EXTRACT(YEAR FROM date) as pYear, 
       ROUND(CAST(MAX(temperature_c * 9/5 + 32) AS NUMERIC), 1) as max_temperature_f
FROM lake_data
WHERE 
    EXTRACT(YEAR FROM date) BETWEEN EXTRACT(YEAR FROM CURRENT_DATE) - 5 
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

# Convert dataframes to JSON format for JavaScript
current_json = df_current.to_json(orient="records", date_format="iso")
df_past.rename(columns={"pyear": "pYear"}, inplace=True)  # Ensure correct column name
df_past["pYear"] = df_past["pYear"].astype(int)  # Convert float year to integer
past_json = df_past.to_json(orient="records", date_format="iso")

# Extract unique years for labeling
# print(df_past.head())  # Debugging step: Check what columns exist
years = df_past["pYear"].unique()  # Use lowercase "pyear" from print output

# Generate the JavaScript dataset definitions
datasets_js = """
const datasets = [
    {
        label: "Current Year",
        data: dataCurrent.map(row => ({ x: new Date(row.date), y: row.max_temperature_f })),
        borderColor: "rgba(75, 192, 192, 1)",
        backgroundColor: "rgba(75, 192, 192, 0.2)",
        fill: false,
        borderWidth: 5, // Make current year thicker
        tension: 0.1
    }
];

const colors = ["rgba(192, 75, 75, 1)", "rgba(192, 192, 75, 1)", "rgba(75, 75, 192, 1)", "rgba(192, 75, 192, 1)", "rgba(75, 192, 75, 1)"];
let colorIndex = 0;

const years = Array.from(new Set(dataPast.map(row => Math.round(row.pYear))));  // Remove decimal

years.forEach(year => {
    const filteredData = dataPast.filter(item => item.pYear === year);
    datasets.push({
        label: `${year}`,  // Fixing label formatting
        data: filteredData.map(row => {
           let pastDate = new Date(row.date);
           pastDate.setFullYear(new Date().getFullYear());  // Normalize the year to current
           return { x: pastDate, y: row.max_temperature_f };
       }),
       borderColor: colors[colorIndex % colors.length],
        borderWidth: 2,
        borderDash: [5, 5], // Dashed lines for previous years
        fill: false,
        tension: 0.1
    });
    colorIndex++;
});"""

# Generate HTML content
html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Lake Sammamish Water Temperature</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns"></script>
       <style>
           @media screen and (max-width: 768px) {
               h1 {
                   font-size: 1.5rem; /* Reduce title size */
                   text-align: center;
               }
               canvas {
                   width: 100% !important;
                   height: auto !important;
               }
           }
       </style>    
</head>
<body>
    <h1>Lake Sammamish Water Temperature</h1>
       <div style="width: 100%; max-width: 1000px; margin: auto;">
           <canvas id="lakeChart"></canvas>
       </div>
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
                responsive: true,  // Make it scale to different screens
                maintainAspectRatio: false,  // Allow dynamic resizing
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
                        }},
                        min: new Date(new Date().setDate(new Date().getDate() - 7)),  // 7 days before today
                        max: new Date(new Date().setDate(new Date().getDate() + 7))   // 7 days after today
                    }},
                    y: {{
                        suggestedMin: 40,
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
import os

output_path = "docs/index.html"

# Ensure the directory exists
os.makedirs(os.path.dirname(output_path), exist_ok=True)

# Write the file
with open(output_path, "w", encoding="utf-8") as file:
    file.write(html_content)

# Debugging: List files in "docs/"
print("Listing contents of 'docs/' directory:")
for filename in os.listdir("docs"):
    print(filename)

output_path = "docs/index.html"

try:
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"✅ Successfully wrote {output_path}")
except Exception as e:
    print(f"❌ Failed to write {output_path}: {e}")



print(f"HTML file successfully created at {output_path}")
