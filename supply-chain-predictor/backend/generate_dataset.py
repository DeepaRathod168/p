"""
generate_dataset.py  (v2.0)
---------------------------
Generates a synthetic dataset of 2,000 delivery records.

New features (v2.0):
  - hour          : departure hour (0–23)
  - day_of_week   : 0=Monday … 6=Sunday
  - peak_hour     : 1 if morning/evening rush
  - is_weekend    : 1 if Saturday/Sunday

Target: delay (0 = On Time, 1 = Delayed)
"""

import numpy as np
import pandas as pd
import random
from datetime import datetime, timedelta

np.random.seed(42)
random.seed(42)

N = 2000

# Scoring maps (higher = worse conditions)
WEATHER_SCORE = {"Sunny": 0, "Rainy": 1, "Storm": 2}
TRAFFIC_SCORE = {"Low": 0, "Medium": 1, "High": 2}
VEHICLE_SCORE = {"Bike": 0, "Van": 1, "Truck": 2}  # 0=fastest, 2=slowest

WEATHER_OPTIONS = list(WEATHER_SCORE.keys())
TRAFFIC_OPTIONS = list(TRAFFIC_SCORE.keys())
VEHICLE_OPTIONS = list(VEHICLE_SCORE.keys())

base_date = datetime(2024, 1, 1)
records = []

for _ in range(N):
    distance    = round(random.uniform(5, 500), 1)
    weather     = random.choice(WEATHER_OPTIONS)
    traffic     = random.choice(TRAFFIC_OPTIONS)
    vehicle     = random.choice(VEHICLE_OPTIONS)

    # Random realistic timestamp
    offset   = timedelta(
        days=random.randint(0, 400),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )
    dt          = base_date + offset
    hour        = dt.hour
    day_of_week = dt.weekday()     # 0=Mon … 6=Sun
    is_weekend  = int(day_of_week >= 5)
    peak_hour   = int((7 <= hour <= 9) or (17 <= hour <= 20))

    ws = WEATHER_SCORE[weather]
    ts = TRAFFIC_SCORE[traffic]
    vs = VEHICLE_SCORE[vehicle]

    # Delay probability — composite rule-based model
    delay_prob = (
        0.04 +
        (distance / 500) * 0.28 +   # longer route → more risk
        ws * 0.16 +                  # bad weather
        ts * 0.14 +                  # heavy traffic
        vs * 0.06 +                  # slow vehicle
        peak_hour * 0.12 +           # rush-hour penalty
        is_weekend * (-0.04)         # weekend slight benefit
    )
    delay_prob = min(max(delay_prob, 0.03), 0.96)
    delay = int(random.random() < delay_prob)

    records.append({
        "distance":    distance,
        "weather":     weather,
        "traffic":     traffic,
        "vehicle_type": vehicle,
        "hour":        hour,
        "day_of_week": day_of_week,
        "peak_hour":   peak_hour,
        "is_weekend":  is_weekend,
        "delay":       delay,
    })

df = pd.DataFrame(records)
df.to_csv("dataset.csv", index=False)
print(f"[DATA] Generated {len(df)} rows")
print(df["delay"].value_counts())
print(df.head())
