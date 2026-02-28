# Lake Sammamish Water Temperature

Live water temperature tracker for Lake Sammamish, WA. Displays the current surface temperature with a chart comparing the last few weeks against historical data from previous years.

**Live site:** [strawbo.github.io/lake-sammamish](https://strawbo.github.io/lake-sammamish)

## How it works

A GitHub Actions pipeline runs every 4 hours to:

1. **Fetch** the current month's water profile data from [King County's lake buoy system](https://green2.kingcounty.gov/lake-buoy/Data.aspx) via the `DataScrape.aspx` endpoint
2. **Import** the data into a Supabase Postgres database (upserts to avoid duplicates)
3. **Generate** a static `docs/index.html` with the latest data baked in as JSON
4. **Push** the updated HTML to GitHub Pages

## Data source

Temperature readings come from King County's lake buoy monitoring program. The buoy measures water temperature at multiple depths throughout the day. This project uses surface readings (depth < 1.5m) converted to Fahrenheit.

## Project structure

```
scripts/
  download_data.py   # Fetches current month's data from King County
  import_data.py     # Parses TSV and upserts into Supabase
  generate_html.py   # Queries DB, injects data into HTML template
templates/
  template.html      # HTML template with Chart.js visualization
docs/
  index.html         # Generated output (served by GitHub Pages)
  chart.js           # Chart rendering logic
  style.css          # Styles
.github/workflows/
  data_pipeline.yml  # Scheduled pipeline (every 4 hours)
```

## Setup

### Requirements

- Python 3.10+
- A Supabase project with a `lake_data` table:

  ```sql
  CREATE TABLE lake_data (
      date TIMESTAMP NOT NULL,
      depth_m NUMERIC NOT NULL,
      temperature_c NUMERIC,
      PRIMARY KEY (date, depth_m)
  );
  ```

### GitHub Secrets

| Secret | Description |
|--------|-------------|
| `SUPABASE_DB_URL` | Postgres connection string for Supabase |
| `GH_PAT` | GitHub personal access token for pushing to the repo |

### Running locally

```bash
pip install requests beautifulsoup4 psycopg2-binary sqlalchemy pandas python-dotenv

# Create a .env file with your Supabase connection string
echo "SUPABASE_DB_URL=postgresql://..." > .env

# Fetch current month's data
python scripts/download_data.py

# Import into database
python scripts/import_data.py

# Generate HTML
python scripts/generate_html.py
```
