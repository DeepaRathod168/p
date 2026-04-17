"""
weather.py
----------
Weather service for ChainPredictAI.
Uses OpenWeatherMap API when an API key is set; otherwise provides
a realistic simulation based on city climate and current month.

To use a real API key:
    Set OWM_API_KEY = "your_key_here"
    Get a free key at: https://openweathermap.org/api
"""

import requests
import random
from datetime import datetime

# ── Configuration ──────────────────────────────────────────
# Replace with your OpenWeatherMap free API key, or leave empty to simulate
OWM_API_KEY = ""

# ── City weather profiles (season-aware simulation) ────────
# Each city has [dry_weight, rainy_weight, storm_weight]
CITY_PROFILES = {
    "Mumbai":            [2, 5, 3],   # Very rainy (coastal)
    "Delhi":             [7, 2, 1],   # Mostly dry
    "New Delhi":         [7, 2, 1],
    "Chennai":           [4, 4, 2],   # Moderate rain
    "Kolkata":           [3, 5, 2],   # Rainy
    "Bangalore":         [5, 4, 1],
    "Bengaluru":         [5, 4, 1],
    "Hyderabad":         [6, 3, 1],
    "Pune":              [5, 4, 1],
    "Ahmedabad":         [7, 2, 1],
    "Jaipur":            [8, 1, 1],   # Desert city – dry
    "Surat":             [4, 5, 1],
    "Kochi":             [2, 6, 2],   # Very rainy (Kerala)
    "Guwahati":          [2, 6, 2],
    "Thiruvananthapuram":[2, 6, 2],
    "Chandigarh":        [6, 3, 1],
    "Goa":               [3, 5, 2],
}

WEATHER_OPTIONS = ["Sunny", "Rainy", "Storm"]


def get_weather(city: str) -> dict:
    """
    Returns weather info dict:
    {condition, description, temperature, humidity, source, icon}
    """
    # Try live OWM API
    if OWM_API_KEY:
        try:
            r = requests.get(
                "http://api.openweathermap.org/data/2.5/weather",
                params={"q": city + ",IN", "appid": OWM_API_KEY},
                timeout=5,
            )
            if r.status_code == 200:
                d = r.json()
                main = d["weather"][0]["main"]
                desc = d["weather"][0]["description"].title()
                temp = round(d["main"]["temp"] - 273.15, 1)
                humidity = d["main"]["humidity"]

                if main in ("Rain", "Drizzle", "Mist", "Fog", "Haze"):
                    condition = "Rainy"
                elif main in ("Thunderstorm", "Tornado", "Squall"):
                    condition = "Storm"
                else:
                    condition = "Sunny"

                return {
                    "condition": condition,
                    "description": desc,
                    "temperature": temp,
                    "humidity": humidity,
                    "source": "api",
                    "icon": _icon(condition),
                }
        except Exception as exc:
            print(f"[WX] OWM error for '{city}': {exc}")

    # Simulate – use city profile, weighted by monsoon season
    month = datetime.now().month
    is_monsoon = 6 <= month <= 9

    city_key = city.strip().title()
    weights = CITY_PROFILES.get(city_key, [5, 3, 2])

    if is_monsoon:
        # Amplify rain/storm weights during monsoon
        weights = [weights[0], weights[1] + 2, weights[2] + 1]

    condition = random.choices(WEATHER_OPTIONS, weights=weights, k=1)[0]

    return {
        "condition": condition,
        "description": f"Simulated — {condition}{'  (Monsoon)' if is_monsoon else ''}",
        "temperature": round(random.uniform(18, 42), 1),
        "humidity": random.randint(35, 92),
        "source": "simulated",
        "icon": _icon(condition),
    }


def _icon(condition: str) -> str:
    return {"Sunny": "☀️", "Rainy": "🌧️", "Storm": "⛈️"}.get(condition, "🌡️")
