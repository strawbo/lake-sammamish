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

    # Skip the header row
    next(csv_reader, None)

    inserted_count = 0  # Count new rows inserted
    updated_count = 0  # Count updated rows

    for row in csv_reader:
        if not row or row[0].strip().lower() == "date":  # Skip empty rows or headers
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
                """
                INSERT INTO lake_data (date, depth_m, temperature_c) 
                VALUES (%s, %s, %s) 
                ON CONFLICT (date, depth_m) 
                DO UPDATE SET temperature_c = EXCLUDED.temperature_c
                RETURNING xmax;
                """,
                (date_time_obj, depth_m, temperature_c)
            )

            # `xmax` is 0 for inserts, nonzero for updates
            result = cursor.fetchone()
            if result and result[0] == 0:
                inserted_count += 1
            else:
                updated_count += 1

# Commit & close connections
conn.commit()
cursor.close()
conn.close()

# Print row count for logging
print(f"Import complete: {inserted_count} new rows inserted, {updated_count} rows updated.")

