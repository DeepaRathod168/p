"""
database.py
-----------
SQLite persistence layer for ChainPredictAI v2.0.
Handles predictions storage, retrieval, and aggregation.
"""

import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(__file__), "chainpredict.db")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id            TEXT PRIMARY KEY,
            timestamp     TEXT NOT NULL,
            source        TEXT NOT NULL,
            destination   TEXT NOT NULL,
            distance      REAL,
            weather       TEXT,
            traffic       TEXT,
            vehicle_type  TEXT,
            hour          INTEGER,
            day_of_week   INTEGER,
            prediction    TEXT,
            delay_probability   REAL,
            ontime_probability  REAL,
            delay_reason  TEXT,
            suggestions   TEXT,
            eta_hours     REAL,
            eta_minutes   INTEGER,
            lat_src       REAL,
            lon_src       REAL,
            lat_dst       REAL,
            lon_dst       REAL
        )
    """)
    # ── Shipment tracking table (v2 addition) ──────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS shipments (
            shipment_id       TEXT PRIMARY KEY,
            source            TEXT NOT NULL,
            destination       TEXT NOT NULL,
            vehicle_type      TEXT DEFAULT 'Van',
            weather           TEXT DEFAULT 'Sunny',
            traffic           TEXT DEFAULT 'Medium',
            distance_km       REAL,
            lat_src           REAL,
            lon_src           REAL,
            lat_dst           REAL,
            lon_dst           REAL,
            delay_probability REAL DEFAULT 0,
            delay_reason      TEXT,
            created_at        TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    print("[DB] Database ready.")


def insert_prediction(record: dict):
    """Persist a prediction record."""
    conn = get_db()
    conn.execute("""
        INSERT OR REPLACE INTO predictions
        (id, timestamp, source, destination, distance, weather, traffic, vehicle_type,
         hour, day_of_week, prediction, delay_probability, ontime_probability,
         delay_reason, suggestions, eta_hours, eta_minutes,
         lat_src, lon_src, lat_dst, lon_dst)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        record["id"], record["timestamp"], record["source"], record["destination"],
        record.get("distance"), record.get("weather"), record.get("traffic"),
        record.get("vehicle_type"), record.get("hour"), record.get("day_of_week"),
        record["prediction"], record["delay_probability"], record["ontime_probability"],
        record.get("delay_reason", ""),
        json.dumps(record.get("suggestions", [])),
        record.get("eta_hours"), record.get("eta_minutes"),
        record.get("lat_src"), record.get("lon_src"),
        record.get("lat_dst"), record.get("lon_dst"),
    ))
    conn.commit()
    conn.close()


def get_recent_predictions(limit: int = 20) -> list:
    """Return the most recent predictions, most recent first."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM predictions ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    result = []
    for row in rows:
        d = dict(row)
        d["suggestions"] = json.loads(d["suggestions"]) if d["suggestions"] else []
        result.append(d)
    return result


def get_dashboard_stats() -> dict:
    """Compute aggregated stats for the dashboard."""
    conn = get_db()

    total = conn.execute("SELECT COUNT(*) as c FROM predictions").fetchone()["c"]
    on_time = conn.execute(
        "SELECT COUNT(*) as c FROM predictions WHERE prediction = 'On Time'"
    ).fetchone()["c"]
    delayed = total - on_time

    weather_rows = conn.execute(
        "SELECT weather, COUNT(*) as cnt FROM predictions WHERE weather IS NOT NULL GROUP BY weather"
    ).fetchall()

    traffic_rows = conn.execute(
        "SELECT traffic, COUNT(*) as cnt FROM predictions WHERE traffic IS NOT NULL GROUP BY traffic"
    ).fetchall()

    trend_rows = conn.execute("""
        SELECT substr(timestamp,1,10) AS date,
               SUM(CASE WHEN prediction='On Time' THEN 1 ELSE 0 END) AS on_time,
               SUM(CASE WHEN prediction='Delayed'  THEN 1 ELSE 0 END) AS delayed
        FROM predictions
        GROUP BY substr(timestamp,1,10)
        ORDER BY date ASC
    """).fetchall()

    conn.close()

    return {
        "total": total,
        "on_time": on_time,
        "delayed": delayed,
        "on_time_pct": round(on_time / total * 100, 1) if total else 0,
        "delayed_pct":  round(delayed / total * 100, 1) if total else 0,
        "weather_breakdown": {r["weather"]: r["cnt"] for r in weather_rows},
        "traffic_breakdown": {r["traffic"]: r["cnt"] for r in traffic_rows},
        "trend": [
            {"date": r["date"], "on_time": r["on_time"], "delayed": r["delayed"]}
            for r in trend_rows
        ],
    }


# ══════════════════════════════════════════════════════════════
#  Shipment tracking CRUD
# ══════════════════════════════════════════════════════════════

def insert_shipment(s: dict):
    """Insert a new shipment record."""
    conn = get_db()
    conn.execute("""
        INSERT OR REPLACE INTO shipments
        (shipment_id, source, destination, vehicle_type, weather, traffic,
         distance_km, lat_src, lon_src, lat_dst, lon_dst,
         delay_probability, delay_reason, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        s["shipment_id"], s["source"], s["destination"],
        s.get("vehicle_type", "Van"), s.get("weather", "Sunny"),
        s.get("traffic", "Medium"), s.get("distance_km"),
        s.get("lat_src"), s.get("lon_src"),
        s.get("lat_dst"), s.get("lon_dst"),
        s.get("delay_probability", 0), s.get("delay_reason", ""),
        s["created_at"],
    ))
    conn.commit()
    conn.close()


def get_shipment(shipment_id: str) -> dict | None:
    """Fetch a single shipment by ID."""
    conn = get_db()
    row  = conn.execute(
        "SELECT * FROM shipments WHERE shipment_id = ?", (shipment_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_shipments_db() -> list:
    """Return all shipments ordered by creation time (newest first)."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM shipments ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_shipment_time(shipment_id: str, new_created_at: str):
    """Rebase the creation timestamp (used for manual status advance)."""
    conn = get_db()
    conn.execute(
        "UPDATE shipments SET created_at = ? WHERE shipment_id = ?",
        (new_created_at, shipment_id),
    )
    conn.commit()
    conn.close()
