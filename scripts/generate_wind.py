"""Fetch wind data from Open-Meteo for Lake Sammamish zones and compute chop scores.

Outputs docs/wind-data.json as a static fallback for the client-side app.
No Supabase dependency — pure API calls.
"""

import json
import requests
from datetime import datetime

# 7 zones along Lake Sammamish
ZONES = [
    {"id": "south_end",      "name": "South End",      "lat": 47.56351, "lon": -122.07801},
    {"id": "south_central",  "name": "South Central",  "lat": 47.57988, "lon": -122.07903},
    {"id": "mid_west",       "name": "The Cove",       "lat": 47.57750, "lon": -122.10888},
    {"id": "mid_east",       "name": "Mid-Lake East",  "lat": 47.60488, "lon": -122.08077},
    {"id": "north_west",     "name": "North West",     "lat": 47.61061, "lon": -122.10565},
    {"id": "ne_shore",       "name": "NE Shore",       "lat": 47.61899, "lon": -122.07136},
    {"id": "north",          "name": "North End",      "lat": 47.63642, "lon": -122.08343},
]

# Sheltering parameters per zone
# fetch_km: how far wind travels over open water before reaching this spot (per 8 directions)
# terrain: how much upwind terrain blocks the wind, 0=none, 1=full (per 8 directions)
# Directions: N, NE, E, SE, S, SW, W, NW
SHELTER_PARAMS = {
    "south_end":     {"fetch": [10.0,5.0, 0.3, 0.2, 0.2,  0.3, 0.3, 3.0], "terrain": [0.0, 0.0, 0.5, 0.6, 0.7, 0.6, 0.7, 0.1]},
    "south_central": {"fetch": [7.0, 3.0, 1.0, 0.5, 2.0,  0.5, 0.5, 4.0], "terrain": [0.0, 0.0, 0.4, 0.5, 0.3, 0.5, 0.7, 0.1]},
    "mid_west":      {"fetch": [4.0, 2.0, 2.0, 1.0, 5.0,  0.2, 0.1, 0.3], "terrain": [0.0, 0.0, 0.0, 0.3, 0.0, 0.8, 0.9, 0.7]},
    "mid_east":      {"fetch": [4.0, 0.3, 0.2, 0.3, 5.0,  5.0, 2.0, 2.0], "terrain": [0.0, 0.4, 0.5, 0.4, 0.0, 0.0, 0.0, 0.0]},
    "north_west":    {"fetch": [0.3, 0.5, 1.5, 4.0, 6.0,  0.2, 0.1, 0.2], "terrain": [0.2, 0.0, 0.0, 0.0, 0.0, 0.8, 0.9, 0.6]},
    "ne_shore":      {"fetch": [2.0, 0.2, 0.2, 0.3, 6.0,  8.0, 2.0, 1.0], "terrain": [0.0, 0.5, 0.5, 0.5, 0.0, 0.0, 0.0, 0.0]},
    "north":         {"fetch": [0.2, 0.3, 0.8, 5.0, 10.0, 6.0, 1.0, 0.2], "terrain": [0.1, 0.1, 0.4, 0.0, 0.0, 0.0, 0.6, 0.2]},
}

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def dir_bucket(deg):
    """Convert wind direction (0-360) to 8-bucket index."""
    return round(deg / 45) % 8


def compute_chop(wind_mph, gust_mph, wind_dir_deg, zone_id):
    """Compute effective wind and chop score for a zone."""
    params = SHELTER_PARAMS[zone_id]
    bucket = dir_bucket(wind_dir_deg)
    fetch_km = params["fetch"][bucket]
    shelter = params["terrain"][bucket]

    effective_wind = wind_mph * (1 - shelter * 0.6)
    fetch_factor = min(1.0, fetch_km / 3.0)

    score = 100
    score -= effective_wind * 7 * fetch_factor
    score -= max(0, gust_mph - wind_mph) * 3 * fetch_factor
    score = max(0, min(100, score))

    return round(effective_wind, 1), round(score)


def chop_label(score):
    if score >= 80:
        return "Glass"
    if score >= 60:
        return "Rideable"
    if score >= 40:
        return "Choppy"
    return "Too Rough"


def fetch_wind():
    """Fetch hourly wind data from Open-Meteo for all zones."""
    lats = ",".join(str(z["lat"]) for z in ZONES)
    lons = ",".join(str(z["lon"]) for z in ZONES)

    params = {
        "latitude": lats,
        "longitude": lons,
        "hourly": "wind_speed_10m,wind_direction_10m,wind_gusts_10m",
        "wind_speed_unit": "mph",
        "timezone": "America/Los_Angeles",
        "forecast_hours": 12,
    }

    resp = requests.get(OPEN_METEO_URL, params=params)
    resp.raise_for_status()
    return resp.json()


def main():
    print("Fetching wind data from Open-Meteo...")
    raw = fetch_wind()

    if not isinstance(raw, list):
        raw = [raw]

    now = datetime.now()
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    current_hour_str = current_hour.strftime("%Y-%m-%dT%H:%M")

    zones_output = []
    for i, zone in enumerate(ZONES):
        hourly = raw[i]["hourly"]
        times = hourly["time"]

        try:
            idx = times.index(current_hour_str)
        except ValueError:
            idx = 0

        zone_hourly = []
        for h in range(min(12, len(times) - idx)):
            hi = idx + h
            wind = hourly["wind_speed_10m"][hi] or 0
            gust = hourly["wind_gusts_10m"][hi] or 0
            direction = hourly["wind_direction_10m"][hi] or 0
            eff_wind, chop = compute_chop(wind, gust, direction, zone["id"])

            zone_hourly.append({
                "time": times[hi],
                "wind_mph": round(wind, 1),
                "wind_dir_deg": round(direction),
                "gust_mph": round(gust, 1),
                "effective_wind_mph": eff_wind,
                "chop_score": chop,
                "chop_label": chop_label(chop),
            })

        current = zone_hourly[0] if zone_hourly else {}
        zones_output.append({
            "id": zone["id"],
            "name": zone["name"],
            "lat": zone["lat"],
            "lon": zone["lon"],
            **current,
            "hourly": zone_hourly,
        })

    best = max(zones_output, key=lambda z: z.get("chop_score", 0))

    output = {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "zones": zones_output,
        "recommendation": {
            "zone_id": best["id"],
            "zone_name": best["name"],
            "chop_score": best.get("chop_score", 0),
            "chop_label": best.get("chop_label", ""),
        },
    }

    with open("docs/wind-data.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote docs/wind-data.json ({len(zones_output)} zones)")
    print(f"Best spot: {best['name']} (chop score: {best.get('chop_score', 'N/A')})")


if __name__ == "__main__":
    main()
