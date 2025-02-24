import psycopg2
import os
import csv
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()  # Load environment variables

DB_URL = os.getenv("SUPABASE_DB_URL")

conn = psycopg2.connect(DB_URL)
cursor = conn.cursor()

with open("SammamishProfile.txt", "r") as file:
    csv_reader = csv.reader(file, delimiter="\t")
    next(csv_reader)  # Skip header

    for row in csv_reader:
        date_time_obj = datetime.strptime(row[0], "%m/%d/%Y %I:%M:%S %p")
        depth = float(row[1])
        temperature = float(row[2])

        cursor.execute("INSERT INTO lake_data (date, depth_m, temperature_c) VALUES (%s, %s, %s) ON CONFLICT (date, depth_m) DO NOTHING",
                       (date_time_obj, depth_m, temperature_c))

conn.commit()
cursor.close()
conn.close()
print("Data import completed.")

