"""Compute swimming comfort scores for Lake Sammamish.

Scores range 0-100 based on weighted factors:
  Water temperature  30%   (from buoy profile data)
  Air temperature    20%   (from Open-Meteo forecast)
  Wind               15%   (from Open-Meteo forecast)
  Sun/radiation      10%   (from Open-Meteo forecast)
  Rain probability   10%   (from Open-Meteo forecast)
  Water clarity       5%   (from buoy turbidity)
  Algae (BGA)        2.5%  (from buoy phycocyanin)
  Air quality        2.5%  (from Open-Meteo AQI)

Hard overrides:
  Phycocyanin > 20 ug/L  -> cap score at 30 (algae bloom)
  AQI > 150              -> cap score at 20 (very unhealthy)
  AQI > 100              -> cap score at 40 (unhealthy for sensitive)
"""

import os
import json
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("SUPABASE_DB_URL")

# --- Scoring curves ---
# Each returns 0-100 for the given input value.


def score_water_temp(f):
    """Water temp in Fahrenheit. Calibrated for cold-sensitive swimmer."""
    if f is None:
        return 50  # neutral if unknown
    points = [(45, 0), (55, 30), (60, 50), (65, 65), (68, 75), (72, 85), (75, 93), (78, 100)]
    return _interpolate(f, points)


def score_air_temp(f):
    """Air temp (feels-like) in Fahrenheit."""
    if f is None:
        return 50
    points = [(50, 0), (60, 30), (68, 60), (75, 80), (80, 93), (85, 100)]
    return _interpolate(f, points)


def score_wind(mph):
    """Wind speed in mph. Calm is best."""
    if mph is None:
        return 50
    points = [(0, 100), (3, 100), (5, 90), (10, 65), (15, 35), (20, 10), (25, 0)]
    return _interpolate(mph, points)


def score_sun(w_per_m2):
    """Solar radiation in W/m2."""
    if w_per_m2 is None:
        return 50
    points = [(0, 0), (50, 10), (100, 30), (300, 60), (500, 85), (700, 100)]
    return _interpolate(w_per_m2, points)


def score_rain(precip_pct):
    """Precipitation probability 0-100%."""
    if precip_pct is None:
        return 50
    return max(0, min(100, 100 - precip_pct))


def score_turbidity(ntu):
    """Water turbidity in NTU. Lower is clearer."""
    if ntu is None:
        return 75  # assume decent if unknown
    points = [(0, 100), (1, 100), (2, 85), (5, 50), (10, 20), (15, 0)]
    return _interpolate(ntu, points)


def score_algae(phycocyanin_ugl):
    """Phycocyanin (blue-green algae proxy) in ug/L."""
    if phycocyanin_ugl is None:
        return 80  # assume low if unknown
    points = [(0, 100), (1, 100), (3, 80), (10, 40), (20, 10), (30, 0)]
    return _interpolate(phycocyanin_ugl, points)


def score_aqi(aqi):
    """US AQI. Lower is better."""
    if aqi is None:
        return 80  # assume good if unknown
    points = [(0, 100), (50, 100), (75, 80), (100, 60), (150, 30), (200, 0)]
    return _interpolate(aqi, points)


def _interpolate(x, points):
    """Linear interpolation between defined points. Clamps at endpoints."""
    if x <= points[0][0]:
        return points[0][1]
    if x >= points[-1][0]:
        return points[-1][1]
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        if x0 <= x <= x1:
            t = (x - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return points[-1][1]


def label_for_score(score):
    if score >= 80:
        return "Excellent"
    elif score >= 60:
        return "Good"
    elif score >= 40:
        return "Fair"
    elif score >= 20:
        return "Poor"
    else:
        return "Unsafe"


WEIGHTS = {
    "water_temp": 0.30,
    "air_temp": 0.20,
    "wind": 0.15,
    "sun": 0.10,
    "rain": 0.10,
    "clarity": 0.05,
    "algae": 0.025,
    "aqi": 0.025,
}
# Remaining 5% is a baseline bonus to make 100 achievable on perfect days
BASELINE_BONUS = 0.05


def compute_score(water_temp_f, feels_like_f, wind_mph, solar_w, precip_pct,
                  turbidity_ntu, phycocyanin_ugl, aqi_val):
    """Compute weighted comfort score with hard overrides."""
    scores = {
        "water_temp": score_water_temp(water_temp_f),
        "air_temp": score_air_temp(feels_like_f),
        "wind": score_wind(wind_mph),
        "sun": score_sun(solar_w),
        "rain": score_rain(precip_pct),
        "clarity": score_turbidity(turbidity_ntu),
        "algae": score_algae(phycocyanin_ugl),
        "aqi": score_aqi(aqi_val),
    }

    weighted = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
    # Baseline bonus: 100 * 0.05 = 5 points on a perfect day
    overall = weighted + 100 * BASELINE_BONUS
    overall = round(min(100, max(0, overall)), 1)

    override_reason = None

    # Hard overrides
    if phycocyanin_ugl is not None and phycocyanin_ugl > 20:
        overall = min(overall, 30)
        override_reason = f"Algae bloom warning (phycocyanin {phycocyanin_ugl} ug/L)"

    if aqi_val is not None and aqi_val > 150:
        overall = min(overall, 20)
        override_reason = f"Very unhealthy air quality (AQI {aqi_val})"
    elif aqi_val is not None and aqi_val > 100:
        overall = min(overall, 40)
        override_reason = (override_reason or "") + f"Unhealthy air quality for sensitive groups (AQI {aqi_val})"

    return overall, label_for_score(overall), scores, override_reason


def get_latest_buoy_data(cursor):
    """Get the most recent surface water observations from the buoy."""
    cursor.execute("""
        SELECT temperature_c, turbidity_ntu, chlorophyll_ugl, phycocyanin_ugl
        FROM lake_data
        WHERE depth_m < 1.5 AND temperature_c IS NOT NULL
        ORDER BY date DESC
        LIMIT 1;
    """)
    row = cursor.fetchone()
    if row:
        temp_c, turbidity, chlorophyll, phycocyanin = row
        temp_f = round(float(temp_c) * 9 / 5 + 32, 1) if temp_c else None
        return {
            "water_temp_f": temp_f,
            "turbidity_ntu": float(turbidity) if turbidity else None,
            "phycocyanin_ugl": float(phycocyanin) if phycocyanin else None,
        }
    return {"water_temp_f": None, "turbidity_ntu": None, "phycocyanin_ugl": None}


def get_forecast_hours(cursor):
    """Get the latest forecast for each hour in the next 8 days."""
    cursor.execute("""
        SELECT DISTINCT ON (forecast_time)
            forecast_time, feels_like_f, wind_speed_mph, solar_radiation_w,
            precip_probability, us_aqi, uv_index, temperature_f
        FROM weather_forecast
        WHERE forecast_time >= NOW()
          AND forecast_time < NOW() + INTERVAL '8 days'
        ORDER BY forecast_time, fetched_at DESC;
    """)
    return cursor.fetchall()


def project_water_temps(buoy_temp_f, forecast_rows):
    """Simple energy-balance model to project surface water temperature.

    Lake Sammamish has high thermal mass so temp changes slowly.
    Each hour, nudge water temp toward an equilibrium driven by air temp
    and solar radiation.

    Returns a list of projected water temps (°F), one per forecast row.
    """
    if buoy_temp_f is None:
        return [None] * len(forecast_rows)

    # Tuning constants (empirically reasonable for a large PNW lake)
    DECAY_RATE = 0.006   # fraction of gap closed per hour toward air-driven equilibrium
    SOLAR_GAIN = 0.0008  # °F per hour per W/m² of solar radiation

    water_f = buoy_temp_f
    projected = []
    for row in forecast_rows:
        air_f = float(row[7]) if row[7] else buoy_temp_f  # temperature_f
        solar_w = float(row[3]) if row[3] else 0

        # Equilibrium: air temp slightly damped (water doesn't fully track air)
        equilibrium = air_f * 0.7 + water_f * 0.3
        # Nudge toward equilibrium
        water_f += (equilibrium - water_f) * DECAY_RATE
        # Solar heating bonus
        water_f += solar_w * SOLAR_GAIN

        projected.append(round(water_f, 1))

    return projected


if __name__ == "__main__":
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    print("Connected to database")

    buoy = get_latest_buoy_data(cursor)
    print(f"Latest buoy: water={buoy['water_temp_f']}F, "
          f"turbidity={buoy['turbidity_ntu']} NTU, "
          f"phycocyanin={buoy['phycocyanin_ugl']} ug/L")

    forecast_rows = get_forecast_hours(cursor)
    print(f"Got {len(forecast_rows)} forecast hours")

    # Project water temperature forward using energy balance model
    water_temps = project_water_temps(buoy["water_temp_f"], forecast_rows)
    print(f"Projected water temps: {water_temps[0]}F -> {water_temps[-1]}F" if water_temps and water_temps[0] else "No water temp projection")

    now = datetime.now()
    batch = []
    for i, row in enumerate(forecast_rows):
        forecast_time, feels_like_f, wind_mph, solar_w, precip_pct, aqi_val, uv_index, air_temp_f = row

        feels_like_f = float(feels_like_f) if feels_like_f else None
        wind_mph = float(wind_mph) if wind_mph else None
        solar_w = float(solar_w) if solar_w else None
        precip_pct = float(precip_pct) if precip_pct else None
        aqi_val = float(aqi_val) if aqi_val else None
        uv_index = float(uv_index) if uv_index else None

        projected_water_f = water_temps[i]

        overall, label, scores, override = compute_score(
            projected_water_f, feels_like_f, wind_mph, solar_w, precip_pct,
            buoy["turbidity_ntu"], buoy["phycocyanin_ugl"], aqi_val
        )

        snapshot = {
            "water_temp_f": projected_water_f,
            "feels_like_f": feels_like_f,
            "wind_mph": wind_mph,
            "solar_w": solar_w,
            "precip_pct": precip_pct,
            "turbidity_ntu": buoy["turbidity_ntu"],
            "phycocyanin_ugl": buoy["phycocyanin_ugl"],
            "aqi": aqi_val,
            "uv_index": uv_index,
        }

        batch.append((
            forecast_time, now, overall, label,
            round(scores["water_temp"], 1), round(scores["air_temp"], 1),
            round(scores["wind"], 1), round(scores["sun"], 1),
            round(scores["rain"], 1), round(scores["clarity"], 1),
            round(scores["algae"], 1), round(scores["aqi"], 1),
            override, json.dumps(snapshot),
        ))

    if batch:
        psycopg2.extras.execute_values(
            cursor,
            """
            INSERT INTO comfort_score (
                score_time, computed_at, overall_score, label,
                water_temp_score, air_temp_score, wind_score, sun_score,
                rain_score, clarity_score, algae_score, aqi_score,
                override_reason, input_snapshot
            ) VALUES %s
            ON CONFLICT (score_time)
            DO UPDATE SET computed_at = EXCLUDED.computed_at,
                          overall_score = EXCLUDED.overall_score,
                          label = EXCLUDED.label,
                          water_temp_score = EXCLUDED.water_temp_score,
                          air_temp_score = EXCLUDED.air_temp_score,
                          wind_score = EXCLUDED.wind_score,
                          sun_score = EXCLUDED.sun_score,
                          rain_score = EXCLUDED.rain_score,
                          clarity_score = EXCLUDED.clarity_score,
                          algae_score = EXCLUDED.algae_score,
                          aqi_score = EXCLUDED.aqi_score,
                          override_reason = EXCLUDED.override_reason,
                          input_snapshot = EXCLUDED.input_snapshot;
            """,
            batch,
            page_size=200
        )

    conn.commit()
    cursor.close()
    conn.close()
    print(f"Computed and saved {len(batch)} comfort scores.")
