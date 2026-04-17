"""
train_model.py
--------------
Trains a Random Forest classifier on the synthetic dataset and saves the model + encoders.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score
import joblib
import os

# ── Load dataset ───────────────────────────────────────────────
df = pd.read_csv("dataset.csv")

# ── Encode categorical features ────────────────────────────────
encoders = {}
for col in ["weather", "traffic", "vehicle_type"]:
    le = LabelEncoder()
    df[col + "_enc"] = le.fit_transform(df[col])
    encoders[col] = le

feature_cols = ["distance", "weather_enc", "traffic_enc", "vehicle_type_enc"]
X = df[feature_cols]
y = df["delay"]

# ── Train / test split ─────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# ── Model ──────────────────────────────────────────────────────
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X_train, y_train)

# ── Evaluate ───────────────────────────────────────────────────
y_pred = clf.predict(X_test)
print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
print(classification_report(y_test, y_pred, target_names=["On Time", "Delayed"]))

# ── Save model and encoders ────────────────────────────────────
joblib.dump(clf, "model.pkl")
joblib.dump(encoders, "encoders.pkl")
print("Model saved -> model.pkl")
print("Encoders saved -> encoders.pkl")
