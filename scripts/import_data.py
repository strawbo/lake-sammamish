import csv
import psycopg2
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DB_URL = os.getenv("SUPABASE_DB_URL")

# Connect to Supabase
conn = psycopg2.connect(DB_URL)
cursor = conn.cursor()

print("Connected to the database")

# Open and process the file inside a `with open` block
with open("SammamishProfile.txt", "r") as file:
    csv_reader = csv.reader(file, delimiter="\t")

    for row in csv_reader:
        if not row:  # Skip empty rows
            continue

        # Convert date format
        try:
            date_time_obj = datetime.strptime(row[0], "%m/%d/%Y %I:%M:%S %p")  
        except ValueError:
            print(f"Skipping invalid date format: {row[0]}")
            continue  # Skip row with invalid date

        # Convert depth value safely
        depth_m = float(row[1]) if row[1] else None  

        # Convert temperature safely
        try:
            temperature_c = float(row[2]) if row[2] else None  
        except ValueError:
            print(f"Skipping invalid temperature value: {row[2]}")
            continue  # Skip row with invalid temperature

        # Insert into Supabase only if temperature is valid
        if temperature_c is not None:
            cursor.execute(
                "INSERT INTO lake_data (date, depth_m, temperature_c) VALUES (%s, %s, %s) "
                "ON CONFLICT (date, depth_m) DO NOTHING",
                (date_time_obj, depth_m, temperature_c)
            )

# Commit & close connections
conn.commit()
cursor.close()
conn.close()

print("Data import complete.")

