"""
geocode.py
----------
Geocoding + Haversine distance using Nominatim (OpenStreetMap).
Falls back to a hardcoded lookup table for major Indian cities —
no API key required.
"""

import requests
import time
from math import radians, sin, cos, sqrt, atan2

# ── Hardcoded fallback for major Indian cities ─────────────
CITY_COORDS = {
    "Mumbai": (19.0760, 72.8777),
    "Delhi": (28.6139, 77.2090),
    "New Delhi": (28.6139, 77.2090),
    "Bangalore": (12.9716, 77.5946),
    "Bengaluru": (12.9716, 77.5946),
    "Chennai": (13.0827, 80.2707),
    "Kolkata": (22.5726, 88.3639),
    "Hyderabad": (17.3850, 78.4867),
    "Pune": (18.5204, 73.8567),
    "Ahmedabad": (23.0225, 72.5714),
    "Jaipur": (26.9124, 75.7873),
    "Surat": (21.1702, 72.8311),
    "Lucknow": (26.8467, 80.9462),
    "Kanpur": (26.4499, 80.3319),
    "Nagpur": (21.1458, 79.0882),
    "Indore": (22.7196, 75.8577),
    "Bhopal": (23.2599, 77.4126),
    "Patna": (25.5941, 85.1376),
    "Vadodara": (22.3072, 73.1812),
    "Agra": (27.1767, 78.0081),
    "Visakhapatnam": (17.6868, 83.2185),
    "Kochi": (9.9312, 76.2673),
    "Coimbatore": (11.0168, 76.9558),
    "Chandigarh": (30.7333, 76.7794),
    "Guwahati": (26.1445, 91.7362),
    "Bhubaneswar": (20.2961, 85.8245),
    "Thiruvananthapuram": (8.5241, 76.9366),
    "Varanasi": (25.3176, 82.9739),
    "Amritsar": (31.6340, 74.8723),
    "Jodhpur": (26.2389, 73.0243),
    "Udaipur": (24.5854, 73.7125),
    "Nashik": (19.9975, 73.7898),
    "Meerut": (28.9845, 77.7064),
    "Raipur": (21.2514, 81.6296),
    "Goa": (15.2993, 74.1240),
    "Madurai": (9.9252, 78.1198),
    "Mysore": (12.2958, 76.6394),
    "Mysuru": (12.2958, 76.6394),
    "Ranchi": (23.3441, 85.3096),
    "Mangalore": (12.9141, 74.8560),
}

_last_request_time = 0
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "ChainPredictAI/2.0 supply-chain-predictor"}


def geocode_city(city: str) -> dict | None:
    """
    Return {'lat', 'lon', 'display_name'} for a city.
    Uses hardcoded table first, then Nominatim.
    """
    # Check hardcoded table first (instant, no rate limit)
    city_key = city.strip().title()
    if city_key in CITY_COORDS:
        lat, lon = CITY_COORDS[city_key]
        return {"lat": lat, "lon": lon, "display_name": city_key + ", India"}

    # Fallback: Nominatim with rate limiting (1 req/s ToS)
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < 1.1:
        time.sleep(1.1 - elapsed)

    try:
        r = requests.get(
            NOMINATIM_URL,
            params={"q": city + ", India", "format": "json", "limit": 1},
            headers=HEADERS,
            timeout=8,
        )
        _last_request_time = time.time()
        data = r.json()
        if data:
            return {
                "lat": float(data[0]["lat"]),
                "lon": float(data[0]["lon"]),
                "display_name": data[0].get("display_name", city),
            }
    except Exception as exc:
        print(f"[GEO] Nominatim error for '{city}': {exc}")

    return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two lat/lon points."""
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return round(R * 2 * atan2(sqrt(a), sqrt(1 - a)), 1)
