# Lake Sammamish Swim Score

Real-time swimming conditions dashboard for Lake Sammamish, WA.
**Live site**: https://strawbo.github.io/lake-sammamish

## Architecture

Static site generated every 4 hours by GitHub Actions. No backend server — data is queried from Supabase PostgreSQL, converted to JSON, injected into an HTML template, and pushed to GitHub Pages.

```
King County Buoy + Open-Meteo APIs
        ↓
  GitHub Actions (every 4 hrs)
        ↓
  download_data.py → import_data.py → fetch_forecast.py → compute_comfort.py → generate_html.py
        ↓
  docs/index.html (static, served by GitHub Pages)
```

## Companion Site

**Seasonal Outlook**: https://strawbo.github.io/lake-sammamish-seasonal
- Repo: `/Users/snielson/dev/Personal/lake-sammamish-seasonal`
- Year-long swim score projections based on historical data
- Shares the same Supabase database (lake_data, met_data tables)
- Nav links connect the two sites

## Key Files

| File | Purpose |
|------|---------|
| `scripts/migrate_db.py` | Database schema migrations (run first in pipeline) |
| `scripts/download_data.py` | Fetches current month's buoy data from King County |
| `scripts/import_data.py` | Parses TSV and upserts to lake_data + met_data |
| `scripts/fetch_forecast.py` | Gets 8-day weather + AQI forecast from Open-Meteo |
| `scripts/compute_comfort.py` | Calculates weighted comfort scores (0-100) |
| `scripts/generate_html.py` | Queries DB, injects JSON into template, writes index.html |
| `scripts/backfill_buoy.py` | Historical King County data 2021-2026 (manual) |
| `scripts/backfill_openmeteo.py` | Historical weather/AQI 2021-2026 (manual, 60min timeout) |
| `templates/template.html` | HTML template with `{{PLACEHOLDER}}` variables |
| `docs/chart.js` | Frontend rendering (~1200 lines, Chart.js) |
| `docs/style.css` | Styling |

## Database Schema (Supabase PostgreSQL)

**lake_data** — Buoy profile readings (15-min intervals, back to 2021)
- PK: `(date, depth_m)`
- Key columns: `temperature_c`, `turbidity_ntu`, `chlorophyll_ugl`, `phycocyanin_ugl`
- Surface readings: `depth_m < 1.5`

**met_data** — Meteorological observations
- PK: `date`
- Columns: `relative_humidity`, `solar_radiation_w`, `pressure_mb`, `wind_speed_ms`, `wind_direction_deg`, `air_temperature_c`, `precipitation_mm`, `us_aqi`
- Source: King County buoy (primary) + Open-Meteo backfill (gap-fill via COALESCE)

**weather_forecast** — Open-Meteo 8-day forecast snapshots
- PK: `(forecast_time, fetched_at)`
- Columns: `temperature_f`, `feels_like_f`, `wind_speed_mph`, `precip_probability`, `cloud_cover`, `uv_index`, `solar_radiation_w`, `us_aqi`, `pm25`

**comfort_score** — Pre-computed swim scores
- PK: `score_time`
- Columns: `overall_score`, `label`, 8 component scores, `override_reason`, `input_snapshot` (JSONB)

## Comfort Score Model

Weighted sum of 8 factors (0-100 scale):

| Factor | Weight | Input | Score curve |
|--------|--------|-------|-------------|
| Water temp | 30% | Buoy (projected forward) | 45°F→0, 72°F→85, 78°F→100 |
| Air temp (feels-like) | 20% | Forecast | 50°F→0, 85°F→100 |
| Wind | 15% | Forecast | 0-3mph→100, 25+mph→0 |
| Sun/Solar | 10% | Forecast | 0W→0, 700W→100 |
| Rain probability | 10% | Forecast | Linear inverse |
| Water clarity | 5% | Buoy turbidity | 0 NTU→100, 15→0 |
| Algae (BGA) | 2.5% | Buoy phycocyanin | 0→100, 30→0 |
| Air quality | 2.5% | Forecast AQI | 0-50→100, 200→0 |
| Baseline bonus | 5% | Fixed | Always 5 pts |

**Hard overrides** (post-calculation caps):
- Phycocyanin > 20 µg/L → cap at 30 (algae bloom)
- AQI > 150 → cap at 20 (very unhealthy)
- AQI > 100 → cap at 40 (unhealthy for sensitive groups)

**Labels**: Excellent (80-100), Good (60-79), Fair (40-59), Poor (20-39), Unsafe (0-19)

## Data Injected into Template

`generate_html.py` replaces these placeholders in `templates/template.html`:

- `{{DATA_CURRENT}}` — 3-week window of current year max surface temps
- `{{DATA_PAST}}` — Past 5 years same-season temps (for year-over-year comparison)
- `{{COMFORT_FORECAST}}` — Hourly comfort scores (yesterday through +8 days)
- `{{CURRENT_COMFORT}}` — Single nearest comfort score to now
- `{{DATA_META}}` — Latest buoy timestamp + generation time
- `{{HIST_WEATHER}}` — Historical weather averages (±7 DOY window) for detail chart reference lines

## Frontend (chart.js)

- **Comfort hero**: Large score ring, label, explanation of limiting factors
- **Conditions pills**: Water temp, feels-like, wind, rain, UV, AQI, clarity — click to open detail chart
- **Detail charts**: Score breakdown (bar), water temp (line with 5-year history), forecast metrics (line with historical avg reference)
- **8-day forecast cards**: Daily score + conditions snapshot
- **Custom Chart.js plugins**: daylight shading, crosshair, "now" line, threshold lines

## GitHub Actions Workflows

- **data_pipeline.yml**: Runs every 4 hours. Full pipeline: migrate → download → import → forecast → comfort → generate → push.
- **backfill.yml**: Manual trigger. Backfills King County buoy + Open-Meteo historical data. 60-min timeout.
- **regenerate_html.yml**: Manual trigger. Regenerates HTML without fetching new data.

## Secrets

- `SUPABASE_DB_URL` — PostgreSQL connection string
- `GH_PAT` — GitHub PAT for pushing commits from Actions

## Git

- Remote: `git@github.com-Personal:strawbo/lake-sammamish.git`
- Branch: `main` only
- Auto-commits from pipeline: "Auto-update index.html"
- GitHub Pages serves from `docs/` directory

## Development Notes

- Python 3.12, deps in `requirements.txt`
- Local `.env` file with `SUPABASE_DB_URL`
- Backfill scripts use COALESCE upserts to avoid overwriting buoy data with Open-Meteo
- Lake coordinates: 47.5912°N, 122.0906°W
- Buoy data marked stale if >12 hours old
