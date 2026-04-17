"""
tracking.py
-----------
Real-time shipment tracking simulation for ChainPredictAI.

Simulates delivery progression using a time-compressed model:
  - SIM_SPEED = 90 → 1 real minute = 90 simulated minutes (1.5 h)
  - Positions are interpolated linearly between source & destination
  - All state is computed from the creation timestamp (stateless)
  - No background threads needed — correct on every API call
"""

from datetime import datetime, timedelta

# ─────────────────────────────────────────────────────────────
#  Simulation parameters
# ─────────────────────────────────────────────────────────────
SIM_SPEED   = 90      # 1 real minute = 90 simulated minutes (1.5 hrs)
MIN_REAL_M  = 5.0     # minimum 5 real minutes for any journey
MAX_REAL_M  = 22.0    # maximum 22 real minutes (nice demo window)

SPEED_MAP = {"Bike": 55, "Van": 75, "Truck": 60}

# ─────────────────────────────────────────────────────────────
#  Status definitions
# ─────────────────────────────────────────────────────────────
STATUS_FLOW = [
    "Order Placed",
    "Packed",
    "Shipped",
    "In Transit",
    "Out for Delivery",
    "Delivered",
]

# (start_pct_inclusive, end_pct_exclusive)
STATUS_RANGES = {
    "Order Placed":     (0,   5),
    "Packed":           (5,  12),
    "Shipped":          (12, 18),
    "In Transit":       (18, 85),
    "Out for Delivery": (85, 97),
    "Delivered":        (97, 101),
}

STATUS_ICONS = {
    "Order Placed":     "📋",
    "Packed":           "📦",
    "Shipped":          "🚀",
    "In Transit":       "🚛",
    "Out for Delivery": "🏡",
    "Delivered":        "✅",
}

# (background, foreground) for UI badge
STATUS_COLORS = {
    "Order Placed":     ("#F1F5F9", "#475569"),
    "Packed":           ("#FEF3C7", "#92400E"),
    "Shipped":          ("#DBEAFE", "#1E40AF"),
    "In Transit":       ("#EDE9FE", "#5B21B6"),
    "Out for Delivery": ("#FFEDD5", "#9A3412"),
    "Delivered":        ("#D1FAE5", "#065F46"),
}

# Progress bar color per status
STATUS_BAR_COLOR = {
    "Order Placed":     "#94A3B8",
    "Packed":           "#F59E0B",
    "Shipped":          "#3B82F6",
    "In Transit":       "#8B5CF6",
    "Out for Delivery": "#F97316",
    "Delivered":        "#10B981",
}

# ─────────────────────────────────────────────────────────────
#  Pure helper functions
# ─────────────────────────────────────────────────────────────

def journey_real_minutes(distance_km: float, vehicle_type: str = "Van") -> float:
    """How many real minutes the simulated journey takes."""
    speed    = SPEED_MAP.get(vehicle_type, 65)
    sim_mins = distance_km / speed * 60           # journey in sim minutes
    real_m   = sim_mins / SIM_SPEED               # compressed real minutes
    return max(MIN_REAL_M, min(MAX_REAL_M, real_m))


def get_status_from_pct(pct: float) -> str:
    """Map progress percentage → status string."""
    for st, (lo, hi) in STATUS_RANGES.items():
        if lo <= pct < hi:
            return st
    return "Delivered"


def interpolate_pos(lat1: float, lon1: float,
                    lat2: float, lon2: float,
                    pct: float) -> tuple:
    """Linearly interpolate lat/lon at pct (0–100)."""
    t = min(max(pct, 0), 100) / 100
    return round(lat1 + t * (lat2 - lat1), 6), round(lon1 + t * (lon2 - lon1), 6)


def _location_label(pct: float, src: str, dst: str) -> str:
    """Human-readable location name based on journey progress."""
    if pct < 5:   return f"{src} Warehouse"
    if pct < 12:  return f"{src} Sorting Hub"
    if pct < 18:  return f"Departed {src}"
    if pct < 35:  return f"En route from {src}"
    if pct < 55:  return f"Midway – {src} → {dst}"
    if pct < 75:  return f"Approaching {dst} region"
    if pct < 85:  return f"Outskirts of {dst}"
    if pct < 97:  return f"{dst} – Last-Mile Delivery"
    return f"Delivered at {dst}"


def fmt_eta(minutes: float) -> str:
    """Format remaining minutes as '2h 15m' or '45m'."""
    if minutes <= 0:
        return "Arrived"
    h, m = int(minutes // 60), int(minutes % 60)
    return f"{h}h {m}m" if h > 0 else f"{m}m"


# ─────────────────────────────────────────────────────────────
#  Core: compute full shipment state (stateless, call anytime)
# ─────────────────────────────────────────────────────────────

def compute_shipment_state(shipment: dict) -> dict:
    """
    Given a raw shipment dict from the DB, compute and return
    a fully enriched state dict including current status, position,
    ETA, timeline history, and rendering metadata.

    This function is pure / stateless — safe and correct to call
    on every HTTP request without any background threads.
    """
    s = dict(shipment)

    distance = float(s.get("distance_km") or 100)
    vehicle  = s.get("vehicle_type", "Van") or "Van"

    real_mins = journey_real_minutes(distance, vehicle)
    created   = datetime.fromisoformat(s["created_at"])
    elapsed   = (datetime.now() - created).total_seconds() / 60

    progress = min((elapsed / real_mins) * 100, 100)
    status   = get_status_from_pct(progress)

    # Position interpolation
    lat1 = float(s.get("lat_src") or 0)
    lon1 = float(s.get("lon_src") or 0)
    lat2 = float(s.get("lat_dst") or 0)
    lon2 = float(s.get("lon_dst") or 0)
    cur_lat, cur_lon = interpolate_pos(lat1, lon1, lat2, lon2, progress)

    # ETA with delay factor
    delay_p   = float(s.get("delay_probability") or 0)
    delay_f   = 1 + (delay_p / 100) * 0.4      # up to 40% extra time
    remaining = max(0, (real_mins - elapsed) * delay_f)

    # Timeline history: one entry per reached status
    history = []
    for st in STATUS_FLOW:
        lo, _ = STATUS_RANGES[st]
        if progress >= lo:
            reached_min = (lo / 100) * real_mins
            reached_at  = created + timedelta(minutes=reached_min)
            history.append({
                "status":    st,
                "icon":      STATUS_ICONS[st],
                "bg":        STATUS_COLORS[st][0],
                "fg":        STATUS_COLORS[st][1],
                "bar_color": STATUS_BAR_COLOR[st],
                "timestamp": reached_at.strftime("%d %b, %H:%M"),
                "location":  _location_label(lo, s["source"], s["destination"]),
            })

    bg, fg = STATUS_COLORS[status]

    s.update({
        # Core state
        "status":               status,
        "status_index":         STATUS_FLOW.index(status),
        "status_icon":          STATUS_ICONS[status],
        "status_bg":            bg,
        "status_fg":            fg,
        "status_bar_color":     STATUS_BAR_COLOR[status],
        "progress_pct":         round(progress, 2),
        # Position
        "current_lat":          cur_lat,
        "current_lon":          cur_lon,
        "current_location_name":_location_label(progress, s["source"], s["destination"]),
        # ETA
        "eta_minutes":          round(remaining),
        "eta_display":          fmt_eta(remaining),
        "delay_factor":         round(delay_f, 3),
        # Flags
        "is_delivered":         progress >= 97,
        # Timeline
        "history":              history,
        # Metadata for frontend rendering
        "status_flow":          STATUS_FLOW,
        "status_icons":         STATUS_ICONS,
        "status_colors":        {k: {"bg": v[0], "fg": v[1]} for k, v in STATUS_COLORS.items()},
        "status_bar_colors":    STATUS_BAR_COLOR,
        # Simulation debug info
        "_journey_real_min":    round(real_mins, 2),
        "_elapsed_min":         round(elapsed, 2),
    })
    return s
