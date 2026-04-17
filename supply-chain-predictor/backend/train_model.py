"""
train_model.py  (v2.0)
----------------------
Trains a Random Forest classifier on the enhanced synthetic dataset.

New in v2.0:
  - 8 features including time-of-day and day-of-week
  - Higher n_estimators + tuned max_depth for better accuracy
  - Saves feature_names.pkl for explainability
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score
import joblib
import os

BASE_DIR = os.path.dirname(__file__)

# ── Load dataset ───────────────────────────────────────────
df = pd.read_csv(os.path.join(BASE_DIR, "dataset.csv"))
print(f"[TRAIN] Loaded {len(df)} rows. Delay rate: {df['delay'].mean():.2%}")

# ── Encode categorical features ────────────────────────────
encoders = {}
for col in ["weather", "traffic", "vehicle_type"]:
    le = LabelEncoder()
    df[col + "_enc"] = le.fit_transform(df[col])
    encoders[col] = le

# ── Feature matrix ─────────────────────────────────────────
feature_cols = [
    "distance",
    "weather_enc",
    "traffic_enc",
    "vehicle_type_enc",
    "hour",
    "day_of_week",
    "peak_hour",
    "is_weekend",
]
FEATURE_NAMES = [
    "Distance (km)",
    "Weather",
    "Traffic",
    "Vehicle Type",
    "Hour of Day",
    "Day of Week",
    "Peak Hour",
    "Is Weekend",
]

X = df[feature_cols]
y = df["delay"]

# ── Train/test split ───────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ── Random Forest (tuned) ──────────────────────────────────
clf = RandomForestClassifier(
    n_estimators=300,
    max_depth=12,
    min_samples_split=4,
    random_state=42,
    n_jobs=-1,
)
clf.fit(X_train, y_train)

# ── Evaluate ───────────────────────────────────────────────
y_pred = clf.predict(X_test)
print(f"\n[EVAL] Accuracy: {accuracy_score(y_test, y_pred):.4f}")
print(classification_report(y_test, y_pred, target_names=["On Time", "Delayed"]))

# ── Feature importance ─────────────────────────────────────
fi = sorted(
    zip(FEATURE_NAMES, clf.feature_importances_),
    key=lambda x: x[1],
    reverse=True,
)
print("\n[FEAT] Feature importances:")
for name, score in fi:
    bar = "#" * int(score * 60)
    print(f"  {name:<22} {score:.4f}  {bar}")

# ── Persist artifacts ──────────────────────────────────────
joblib.dump(clf,          os.path.join(BASE_DIR, "model.pkl"))
joblib.dump(encoders,     os.path.join(BASE_DIR, "encoders.pkl"))
joblib.dump(FEATURE_NAMES, os.path.join(BASE_DIR, "feature_names.pkl"))

print("\n[SAVE] model.pkl, encoders.pkl, feature_names.pkl written.")
