"""
app.py  (v2.0)
--------------
ChainPredictAI – Production-grade Flask backend.

New in v2.0:
  ✅ SQLite database (persistent history)
  ✅ /route  endpoint – geocoding + distance auto-calculation
  ✅ /weather endpoint – real-time weather (OWM or simulation)
  ✅ /traffic endpoint – time-based traffic simulation
  ✅ /predict (enhanced) – 8-feature model, ETA, XAI explanation
  ✅ /history  – served from SQLite, supports ?limit=
  ✅ /dashboard – aggregated stats from DB
  ✅ /health   – readiness probe

Explainable AI: rule-based delay reason derived from input features.
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import joblib
import os
import uuid
from datetime import datetime
import numpy as np

# ── Local modules ──────────────────────────────────────────
from database import (
    init_db, insert_prediction, get_recent_predictions, get_dashboard_stats,
    # Tracking
    insert_shipment, get_shipment, get_all_shipments_db, update_shipment_time,
)
from services.geocode  import geocode_city, haversine_km
from services.weather  import get_weather
from services.traffic  import get_traffic_level

# ── App setup ──────────────────────────────────────────────
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)

# ── Database ───────────────────────────────────────────────
init_db()

# ── Load ML model ──────────────────────────────────────────
BASE_DIR      = os.path.dirname(__file__)
MODEL_READY   = False
clf           = None
encoders      = None
FEATURE_NAMES = []

try:
    clf           = joblib.load(os.path.join(BASE_DIR, "model.pkl"))
    encoders      = joblib.load(os.path.join(BASE_DIR, "encoders.pkl"))
    FEATURE_NAMES = joblib.load(os.path.join(BASE_DIR, "feature_names.pkl"))
    MODEL_READY   = True
    print("[OK] Model + encoders loaded.")
except FileNotFoundError as e:
    print(f"[WARN] Model files missing: {e}")
    print("       Run: python generate_dataset.py && python train_model.py")


# ══════════════════════════════════════════════════════════
#  Explainability & Suggestions
# ══════════════════════════════════════════════════════════

def explain_delay(
    distance: float, weather: str, traffic: str,
    vehicle: str, hour: int, day_of_week: int,
    delay_prob: float,
) -> str:
    """Build a human-readable delay explanation from key features."""
    factors = []

    if distance > 300:
        factors.append(f"long route ({distance:.0f} km)")
    elif distance > 150:
        factors.append(f"moderate distance ({distance:.0f} km)")

    if weather == "Storm":
        factors.append("severe storm conditions")
    elif weather == "Rainy":
        factors.append("rainy weather slowing traffic")

    if traffic == "High":
        factors.append("heavy traffic congestion")
    elif traffic == "Medium":
        factors.append("moderate traffic")

    if vehicle == "Truck" and distance > 200:
        factors.append("truck limitations on long haul")
    elif vehicle == "Bike" and distance > 100:
        factors.append("bike unsuitable for long distance")

    if (7 <= hour <= 9) or (17 <= hour <= 20):
        factors.append("peak rush-hour departure")

    if day_of_week == 0:
        factors.append("Monday congestion surge")

    if not factors:
        if delay_prob < 25:
            return "✅ Low risk: favorable conditions across all factors."
        factors.append("minor cumulative risk factors")

    if delay_prob >= 70:
        prefix = "⚠️ High delay risk:"
    elif delay_prob >= 40:
        prefix = "⚡ Moderate delay risk:"
    else:
        prefix = "ℹ️ Low delay risk —"

    return f"{prefix} {', '.join(factors)}."


def get_suggestions(
    distance: float, weather: str, traffic: str,
    vehicle: str, hour: int, day_of_week: int,
) -> list:
    """Return a prioritised list of actionable suggestions."""
    sug = []

    if traffic == "High":
        sug.append({
            "type": "traffic", "icon": "🕐", "priority": "high",
            "title": "Avoid Peak Traffic Hours",
            "reason": "High traffic detected — schedule before 8 AM or after 8 PM.",
        })
        sug.append({
            "type": "route", "icon": "🗺️", "priority": "medium",
            "title": "Consider Alternate Routes",
            "reason": "Bypass roads or ring roads can save 20–35 minutes.",
        })

    if weather in ("Rainy", "Storm"):
        sug.append({
            "type": "weather", "icon": "🌧️", "priority": "high",
            "title": "Delay Shipment if Possible",
            "reason": f"{weather} conditions raise accident risk and slow all vehicles.",
        })

    if vehicle == "Bike" and distance > 100:
        sug.append({
            "type": "vehicle", "icon": "🚚", "priority": "medium",
            "title": "Switch to Van or Truck",
            "reason": f"Bike is unreliable for {distance:.0f} km. A van is faster & safer.",
        })

    if vehicle == "Truck" and distance < 50:
        sug.append({
            "type": "vehicle", "icon": "🏍️", "priority": "low",
            "title": "Use a Bike or Van",
            "reason": f"Trucks are slow for short {distance:.0f} km runs.",
        })

    if (7 <= hour <= 9) or (17 <= hour <= 20):
        sug.append({
            "type": "time", "icon": "⏰", "priority": "high",
            "title": "Reschedule Departure",
            "reason": "Currently in peak hours. Departing off-peak saves 20–40 min.",
        })

    if traffic == "High" or weather in ("Rainy", "Storm"):
        sug.append({
            "type": "time", "icon": "✨", "priority": "medium",
            "title": "Best Departure Window",
            "reason": "Early morning (5–7 AM) or late evening (9 PM+) with clear skies.",
        })

    if distance > 300 and weather == "Sunny" and traffic == "Low":
        sug.append({
            "type": "route", "icon": "✅", "priority": "low",
            "title": "Optimal Conditions",
            "reason": "Great weather and light traffic — perfect time to depart!",
        })

    if not sug:
        sug.append({
            "type": "info", "icon": "ℹ️", "priority": "low",
            "title": "Conditions Look Acceptable",
            "reason": "No major risk factors detected. Proceed as planned.",
        })

    return sug


# ══════════════════════════════════════════════════════════
#  Static file serving
# ══════════════════════════════════════════════════════════

API_PREFIXES = {"predict", "route", "weather", "traffic", "history", "dashboard", "health"}

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if path and path.split("/")[0] in API_PREFIXES:
        from flask import abort
        abort(404)
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
    if path and os.path.exists(os.path.join(static_dir, path)):
        return send_from_directory(static_dir, path)
    return send_from_directory(static_dir, "index.html")


# ══════════════════════════════════════════════════════════
#  API Endpoints
# ══════════════════════════════════════════════════════════

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model_ready": MODEL_READY, "version": "2.0"})


# ── GET /weather?city=<name> ───────────────────────────────
@app.route("/weather", methods=["GET"])
def weather_endpoint():
    city = request.args.get("city", "").strip()
    if not city:
        return jsonify({"error": "city parameter is required"}), 400
    return jsonify(get_weather(city))


# ── GET /route?source=<>&destination=<> ──────────────────
@app.route("/route", methods=["GET"])
def route_endpoint():
    source = request.args.get("source", "").strip()
    destination = request.args.get("destination", "").strip()
    if not source or not destination:
        return jsonify({"error": "Both source and destination are required"}), 400

    src_geo = geocode_city(source)
    dst_geo = geocode_city(destination)

    if not src_geo:
        return jsonify({"error": f"Could not locate city: {source}"}), 404
    if not dst_geo:
        return jsonify({"error": f"Could not locate city: {destination}"}), 404

    straight_km = haversine_km(src_geo["lat"], src_geo["lon"], dst_geo["lat"], dst_geo["lon"])
    road_km     = round(straight_km * 1.3, 1)   # road factor ≈ 1.3×

    return jsonify({
        "source":      {"name": source,      **src_geo},
        "destination": {"name": destination, **dst_geo},
        "straight_line_km":  straight_km,
        "estimated_road_km": road_km,
    })


# ── GET /traffic ──────────────────────────────────────────
@app.route("/traffic", methods=["GET"])
def traffic_endpoint():
    now  = datetime.now()
    data = get_traffic_level(now.hour, now.weekday())
    return jsonify(data)


# ── POST /predict ─────────────────────────────────────────
@app.route("/predict", methods=["POST"])
def predict():
    if not MODEL_READY:
        return jsonify({
            "error": "Model not ready. Run generate_dataset.py then train_model.py."
        }), 503

    data = request.get_json(force=True)
    now  = datetime.now()

    # Required fields
    source      = data.get("source", "").strip()
    destination = data.get("destination", "").strip()
    if not source or not destination:
        return jsonify({"error": "source and destination are required"}), 400

    # ── Distance ──────────────────────────────────────────
    lat_src = lon_src = lat_dst = lon_dst = None
    provided_dist = data.get("distance")

    if provided_dist:
        try:
            distance = float(provided_dist)
        except (TypeError, ValueError):
            return jsonify({"error": "distance must be a number"}), 400
        lat_src = data.get("lat_src")
        lon_src = data.get("lon_src")
        lat_dst = data.get("lat_dst")
        lon_dst = data.get("lon_dst")
    else:
        # Auto-calculate via geocoding
        src_geo = geocode_city(source)
        dst_geo = geocode_city(destination)
        if src_geo and dst_geo:
            straight  = haversine_km(src_geo["lat"], src_geo["lon"],
                                     dst_geo["lat"], dst_geo["lon"])
            distance  = round(straight * 1.3, 1)
            lat_src, lon_src = src_geo["lat"], src_geo["lon"]
            lat_dst, lon_dst = dst_geo["lat"], dst_geo["lon"]
        else:
            return jsonify({
                "error": "Could not calculate distance. Please enter distance manually."
            }), 400

    # ── Weather ───────────────────────────────────────────
    weather = data.get("weather", "").strip()
    if not weather:
        weather = get_weather(source)["condition"]

    # ── Traffic ───────────────────────────────────────────
    traffic = data.get("traffic", "").strip()
    if not traffic:
        traffic = get_traffic_level(now.hour, now.weekday())["level"]

    # ── Vehicle ───────────────────────────────────────────
    vehicle = data.get("vehicle_type", "Van").strip() or "Van"

    # ── Validate enums ────────────────────────────────────
    valid = {
        "Weather":      (weather,  ["Sunny", "Rainy", "Storm"]),
        "Traffic":      (traffic,  ["Low", "Medium", "High"]),
        "Vehicle Type": (vehicle,  ["Bike", "Van", "Truck"]),
    }
    for field, (val, opts) in valid.items():
        if val not in opts:
            return jsonify({"error": f"{field} must be one of {opts}"}), 400

    # ── Time features ─────────────────────────────────────
    hour        = int(data.get("hour",        now.hour))
    day_of_week = int(data.get("day_of_week", now.weekday()))
    peak_hour   = int((7 <= hour <= 9) or (17 <= hour <= 20))
    is_weekend  = int(day_of_week >= 5)

    # ── Encode & predict ──────────────────────────────────
    w_enc = int(encoders["weather"].transform([weather])[0])
    t_enc = int(encoders["traffic"].transform([traffic])[0])
    v_enc = int(encoders["vehicle_type"].transform([vehicle])[0])

    X = np.array([[distance, w_enc, t_enc, v_enc, hour, day_of_week, peak_hour, is_weekend]])
    pred_val    = int(clf.predict(X)[0])
    proba       = clf.predict_proba(X)[0]
    delay_prob  = round(float(proba[1]) * 100, 1)
    ontime_prob = round(float(proba[0]) * 100, 1)
    label       = "Delayed" if pred_val == 1 else "On Time"

    # ── Explainability ────────────────────────────────────
    delay_reason = explain_delay(
        distance, weather, traffic, vehicle, hour, day_of_week, delay_prob
    )
    suggestions = get_suggestions(distance, weather, traffic, vehicle, hour, day_of_week)

    # ── ETA estimate ──────────────────────────────────────
    speed_map  = {"Bike": 55, "Van": 75, "Truck": 60}
    speed_kmh  = speed_map.get(vehicle, 65)
    base_h     = distance / speed_kmh
    delay_f    = 1 + (delay_prob / 100) * 0.6   # up to 60% extra time
    eta_hours  = round(base_h * delay_f, 2)
    eta_mins   = int(eta_hours * 60)

    record = {
        "id":               str(uuid.uuid4())[:8],
        "timestamp":        now.strftime("%Y-%m-%d %H:%M"),
        "source":           source,
        "destination":      destination,
        "distance":         distance,
        "weather":          weather,
        "traffic":          traffic,
        "vehicle_type":     vehicle,
        "hour":             hour,
        "day_of_week":      day_of_week,
        "prediction":       label,
        "delay_probability":  delay_prob,
        "ontime_probability": ontime_prob,
        "delay_reason":     delay_reason,
        "suggestions":      suggestions,
        "eta_hours":        eta_hours,
        "eta_minutes":      eta_mins,
        "lat_src":          lat_src,
        "lon_src":          lon_src,
        "lat_dst":          lat_dst,
        "lon_dst":          lon_dst,
    }

    insert_prediction(record)
    return jsonify(record), 200


# ── GET /history?limit=<N> ────────────────────────────────
@app.route("/history", methods=["GET"])
def history():
    limit = min(int(request.args.get("limit", 20)), 100)
    records = get_recent_predictions(limit)
    return jsonify(records), 200


# ── GET /dashboard ────────────────────────────────────────
@app.route("/dashboard", methods=["GET"])
def dashboard():
    return jsonify(get_dashboard_stats()), 200


# ════════════════════════════════════════════════════════════
#  SHIPMENT TRACKING ENDPOINTS
# ════════════════════════════════════════════════════════════

# ── GET /all-shipments ─────────────────────────────────────
@app.route("/all-shipments", methods=["GET"])
def all_shipments():
    """Return all shipments with freshly computed tracking state."""
    from services.tracking import compute_shipment_state
    raw      = get_all_shipments_db()
    computed = [compute_shipment_state(s) for s in raw]
    return jsonify(computed), 200


# ── POST /create-shipment ──────────────────────────────────
@app.route("/create-shipment", methods=["POST"])
def create_shipment():
    """
    Body: { source, destination, vehicle_type }
    Geocodes cities, fetches live weather/traffic,
    runs ML delay prediction, persists and returns full tracking state.
    """
    from services.tracking import compute_shipment_state

    data    = request.get_json(force=True)
    source  = data.get("source",  "").strip()
    dest    = data.get("destination", "").strip()
    vehicle = data.get("vehicle_type", "Van").strip() or "Van"

    if not source or not dest:
        return jsonify({"error": "source and destination are required"}), 400
    if vehicle not in ["Bike", "Van", "Truck"]:
        return jsonify({"error": "vehicle_type must be Bike, Van, or Truck"}), 400

    now = datetime.now()

    # Geocode + distance
    lat_src = lon_src = lat_dst = lon_dst = None
    distance_km = 500.0
    src_geo = geocode_city(source)
    dst_geo = geocode_city(dest)
    if src_geo and dst_geo:
        lat_src, lon_src = src_geo["lat"], src_geo["lon"]
        lat_dst, lon_dst = dst_geo["lat"], dst_geo["lon"]
        distance_km = round(haversine_km(lat_src, lon_src, lat_dst, lon_dst) * 1.3, 1)

    # Weather + traffic
    wx      = get_weather(source)
    weather = wx["condition"]
    tr      = get_traffic_level(now.hour, now.weekday())
    traffic = tr["level"]

    # ML delay prediction
    delay_prob   = 0.0
    delay_reason = ""
    if MODEL_READY:
        try:
            w_enc  = int(encoders["weather"].transform([weather])[0])
            t_enc  = int(encoders["traffic"].transform([traffic])[0])
            v_enc  = int(encoders["vehicle_type"].transform([vehicle])[0])
            hour   = now.hour
            dow    = now.weekday()
            peak   = int((7 <= hour <= 9) or (17 <= hour <= 20))
            is_wkd = int(dow >= 5)
            X_trk  = np.array([[distance_km, w_enc, t_enc, v_enc, hour, dow, peak, is_wkd]])
            proba  = clf.predict_proba(X_trk)[0]
            delay_prob   = round(float(proba[1]) * 100, 1)
            delay_reason = explain_delay(
                distance_km, weather, traffic, vehicle, hour, dow, delay_prob
            )
        except Exception as exc:
            print(f"[TRACK] ML error: {exc}")

    # Build + persist shipment
    shipment_id = str(uuid.uuid4())[:10].upper()
    raw_data = {
        "shipment_id":       shipment_id,
        "source":            source,
        "destination":       dest,
        "vehicle_type":      vehicle,
        "weather":           weather,
        "traffic":           traffic,
        "distance_km":       distance_km,
        "lat_src":           lat_src,
        "lon_src":           lon_src,
        "lat_dst":           lat_dst,
        "lon_dst":           lon_dst,
        "delay_probability": delay_prob,
        "delay_reason":      delay_reason,
        "created_at":        now.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    insert_shipment(raw_data)
    return jsonify(compute_shipment_state(raw_data)), 201


# ── GET /track/<shipment_id> ───────────────────────────────
@app.route("/track/<shipment_id>", methods=["GET"])
def track_shipment(shipment_id):
    """Return the current computed tracking state for one shipment."""
    from services.tracking import compute_shipment_state
    raw = get_shipment(shipment_id)
    if not raw:
        return jsonify({"error": f"Shipment '{shipment_id}' not found"}), 404
    return jsonify(compute_shipment_state(raw)), 200


# ── POST /update-status/<shipment_id> ─────────────────────
@app.route("/update-status/<shipment_id>", methods=["POST"])
def update_shipment_status(shipment_id):
    """
    Advance shipment to next status (demo / manual override).
    Rebases 'created_at' so the stateless compute returns next status.
    """
    from services.tracking import (
        compute_shipment_state, STATUS_FLOW, STATUS_RANGES,
        journey_real_minutes,
    )
    from datetime import timedelta

    raw = get_shipment(shipment_id)
    if not raw:
        return jsonify({"error": "Shipment not found"}), 404

    current = compute_shipment_state(raw)
    idx     = current["status_index"]

    if idx >= len(STATUS_FLOW) - 1:
        return jsonify({"error": "Already delivered", **current}), 409

    next_status    = STATUS_FLOW[idx + 1]
    next_start_pct = STATUS_RANGES[next_status][0]
    real_mins      = journey_real_minutes(
        raw.get("distance_km") or 100, raw.get("vehicle_type") or "Van"
    )
    target_min  = (next_start_pct / 100) * real_mins
    new_ts      = (datetime.now() - timedelta(minutes=target_min)).strftime("%Y-%m-%dT%H:%M:%S")

    update_shipment_time(shipment_id, new_ts)
    raw["created_at"] = new_ts
    return jsonify(compute_shipment_state(raw)), 200


# ════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("[START] ChainPredictAI v2.0  ->  http://localhost:5000")
    app.run(debug=True, port=5000)

