"""
generate_dataset.py
-------------------
Generates a synthetic dataset of 1000 delivery records for training the ML model.
Features: distance, weather, traffic, vehicle_type → target: delay (0 or 1)
"""

import numpy as np
import pandas as pd
import random

np.random.seed(42)
random.seed(42)

N = 1000

weather_map = {"Sunny": 0, "Rainy": 1, "Storm": 2}
traffic_map = {"Low": 0, "Medium": 1, "High": 2}
vehicle_map = {"Bike": 0, "Van": 1, "Truck": 2}

weather_options = list(weather_map.keys())
traffic_options = list(traffic_map.keys())
vehicle_options = list(vehicle_map.keys())

records = []
for _ in range(N):
    distance = round(random.uniform(5, 500), 1)  # km
    weather = random.choice(weather_options)
    traffic = random.choice(traffic_options)
    vehicle = random.choice(vehicle_options)

    w_score = weather_map[weather]   # 0, 1, 2
    t_score = traffic_map[traffic]   # 0, 1, 2
    v_score = vehicle_map[vehicle]   # 0=fast, 2=slow

    # Delay probability based on realistic rules
    delay_prob = (
        0.05 +
        (distance / 500) * 0.3 +
        w_score * 0.18 +
        t_score * 0.15 +
        v_score * 0.07
    )
    delay_prob = min(delay_prob, 0.97)
    delay = int(random.random() < delay_prob)

    records.append({
        "distance": distance,
        "weather": weather,
        "traffic": traffic,
        "vehicle_type": vehicle,
        "delay": delay
    })

df = pd.DataFrame(records)
df.to_csv("dataset.csv", index=False)
print(f"Dataset generated: {len(df)} rows")
print(df["delay"].value_counts())
print(df.head())
