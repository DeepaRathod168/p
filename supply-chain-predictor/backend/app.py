"""
app.py
------
Flask backend for the Supply Chain Delay Predictor.

Endpoints:
  POST /predict        → Predict delay + probability
  GET  /history        → Retrieve last 10 predictions
  GET  /dashboard      → Get aggregated stats for the dashboard
  GET  /health         → Health-check
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import joblib
import os
import json
import uuid
from datetime import datetime
import numpy as np

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

app = Flask(__name__, static_folder=os.path.abspath(FRONTEND_DIR), static_url_path="")
CORS(app)  # Allow cross-origin requests

# ── Load model & encoders ──────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)

try:
    clf = joblib.load(os.path.join(BASE_DIR, "model.pkl"))
    encoders = joblib.load(os.path.join(BASE_DIR, "encoders.pkl"))
    print("[OK] Model and encoders loaded successfully.")
    MODEL_READY = True
except FileNotFoundError:
    print("[WARN] model.pkl or encoders.pkl not found. Run generate_dataset.py then train_model.py first.")
    MODEL_READY = False

# ── In-memory prediction history (last 30) ────────────────────
HISTORY: list[dict] = []
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")

def load_history():
    """Load persisted history from disk on startup."""
    global HISTORY
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                HISTORY = json.load(f)
        except Exception:
            HISTORY = []

def save_history():
    """Persist history to disk so it survives restarts."""
    with open(HISTORY_FILE, "w") as f:
        json.dump(HISTORY[-30:], f, indent=2)

load_history()

# ─────────────────────────────────────────────────────────────
#  Route-suggestion logic (rule-based)
# ─────────────────────────────────────────────────────────────

def get_suggestions(distance: float, weather: str, traffic: str, vehicle: str) -> list[dict]:
    """Return a list of actionable suggestions with reasoning."""
    suggestions = []

    if traffic == "High":
        suggestions.append({
            "type": "traffic",
            "icon": "🕐",
            "title": "Avoid Peak Traffic Hours",
            "reason": "High traffic detected — schedule delivery before 8 AM or after 8 PM."
        })
        suggestions.append({
            "type": "route",
            "icon": "🗺️",
            "title": "Take Alternate Route",
            "reason": "Main roads are congested. Bypass roads can save 20–35 minutes."
        })

    if weather in ("Rainy", "Storm"):
        suggestions.append({
            "type": "weather",
            "icon": "🌧️",
            "title": "Delay Shipment if Possible",
            "reason": f"{weather} conditions increase accident risk. Consider rescheduling."
        })

    if vehicle == "Bike" and distance > 100:
        suggestions.append({
            "type": "vehicle",
            "icon": "🚚",
            "title": "Switch to a Van or Truck",
            "reason": f"Bike is not optimal for {distance} km. A van offers better reliability."
        })

    if vehicle == "Truck" and distance < 30:
        suggestions.append({
            "type": "vehicle",
            "icon": "🏍️",
            "title": "Use a Bike or Van Instead",
            "reason": f"Trucks are slow in short distances ({distance} km). A bike/van is faster."
        })

    if distance > 300 and weather == "Sunny" and traffic == "Low":
        suggestions.append({
            "type": "route",
            "icon": "✅",
            "title": "Optimal Conditions",
            "reason": "Great weather and low traffic — this is the best time to depart!"
        })

    if not suggestions:
        suggestions.append({
            "type": "info",
            "icon": "ℹ️",
            "title": "Conditions Look Acceptable",
            "reason": "No major issues detected. Proceed with the delivery as planned."
        })

    return suggestions


# ─────────────────────────────────────────────────────────────
#  API Endpoints
# ─────────────────────────────────────────────────────────────

@app.route("/", defaults={"path": ""}, methods=["GET"])
@app.route("/<path:path>", methods=["GET"])
def serve_frontend(path):
    """Serve the React/HTML frontend for any non-API route."""
    # Only serve static files, not API paths
    api_routes = ["predict", "history", "dashboard", "health"]
    if path and path.split("/")[0] in api_routes:
        from flask import abort
        abort(404)  # Let Flask route to the API handlers
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
    if path and os.path.exists(os.path.join(static_dir, path)):
        return send_from_directory(static_dir, path)
    return send_from_directory(static_dir, "index.html")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model_ready": MODEL_READY})


@app.route("/predict", methods=["POST"])
def predict():
    if not MODEL_READY:
        return jsonify({"error": "Model not trained yet. Run generate_dataset.py and train_model.py first."}), 503

    data = request.get_json(force=True)

    # ── Validate required fields ───────────────────────────────
    required = ["source", "destination", "distance", "weather", "traffic", "vehicle_type"]
    for field in required:
        if field not in data or str(data[field]).strip() == "":
            return jsonify({"error": f"Missing field: {field}"}), 400

    try:
        distance = float(data["distance"])
    except ValueError:
        return jsonify({"error": "Distance must be a number."}), 400

    weather = data["weather"]
    traffic = data["traffic"]
    vehicle = data["vehicle_type"]

    valid_weather = ["Sunny", "Rainy", "Storm"]
    valid_traffic = ["Low", "Medium", "High"]
    valid_vehicle = ["Bike", "Van", "Truck"]

    if weather not in valid_weather:
        return jsonify({"error": f"Weather must be one of {valid_weather}"}), 400
    if traffic not in valid_traffic:
        return jsonify({"error": f"Traffic must be one of {valid_traffic}"}), 400
    if vehicle not in valid_vehicle:
        return jsonify({"error": f"Vehicle type must be one of {valid_vehicle}"}), 400

    # ── Encode & predict ───────────────────────────────────────
    w_enc = encoders["weather"].transform([weather])[0]
    t_enc = encoders["traffic"].transform([traffic])[0]
    v_enc = encoders["vehicle_type"].transform([vehicle])[0]

    X = np.array([[distance, w_enc, t_enc, v_enc]])
    prediction = int(clf.predict(X)[0])
    proba = clf.predict_proba(X)[0]
    delay_prob = float(proba[1])
    ontime_prob = float(proba[0])

    label = "Delayed" if prediction == 1 else "On Time"
    suggestions = get_suggestions(distance, weather, traffic, vehicle)

    # ── Build result record ────────────────────────────────────
    record = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": data["source"],
        "destination": data["destination"],
        "distance": distance,
        "weather": weather,
        "traffic": traffic,
        "vehicle_type": vehicle,
        "prediction": label,
        "delay_probability": round(delay_prob * 100, 1),
        "ontime_probability": round(ontime_prob * 100, 1),
        "suggestions": suggestions,
    }

    HISTORY.append(record)
    # Keep only last 30
    if len(HISTORY) > 30:
        HISTORY.pop(0)
    save_history()

    return jsonify(record), 200


@app.route("/history", methods=["GET"])
def history():
    """Return the last 10 predictions (most recent first)."""
    recent = list(reversed(HISTORY[-10:]))
    return jsonify(recent), 200


@app.route("/dashboard", methods=["GET"])
def dashboard():
    """Return aggregated stats for dashboard charts."""
    total = len(HISTORY)
    if total == 0:
        return jsonify({
            "total": 0,
            "on_time": 0,
            "delayed": 0,
            "on_time_pct": 0,
            "delayed_pct": 0,
            "trend": [],
            "weather_breakdown": {},
            "traffic_breakdown": {},
        }), 200

    on_time = sum(1 for r in HISTORY if r["prediction"] == "On Time")
    delayed = total - on_time

    # Build daily trend (group by date substring)
    from collections import defaultdict
    daily: dict = defaultdict(lambda: {"on_time": 0, "delayed": 0})
    for r in HISTORY:
        date_key = r["timestamp"][:10]
        if r["prediction"] == "On Time":
            daily[date_key]["on_time"] += 1
        else:
            daily[date_key]["delayed"] += 1

    trend = [
        {"date": d, "on_time": v["on_time"], "delayed": v["delayed"]}
        for d, v in sorted(daily.items())
    ]

    # Weather breakdown
    weather_counts: dict = defaultdict(int)
    for r in HISTORY:
        weather_counts[r["weather"]] += 1

    # Traffic breakdown
    traffic_counts: dict = defaultdict(int)
    for r in HISTORY:
        traffic_counts[r["traffic"]] += 1

    return jsonify({
        "total": total,
        "on_time": on_time,
        "delayed": delayed,
        "on_time_pct": round(on_time / total * 100, 1),
        "delayed_pct": round(delayed / total * 100, 1),
        "trend": trend,
        "weather_breakdown": dict(weather_counts),
        "traffic_breakdown": dict(traffic_counts),
    }), 200


if __name__ == "__main__":
    print("[START] Supply Chain Delay Predictor API starting on http://localhost:5000")
    app.run(debug=True, port=5000)
