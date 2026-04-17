"""
traffic.py
----------
Traffic simulation service for ChainPredictAI.
Calculates traffic level based on time-of-day and day-of-week patterns
mimicking real-world Indian urban logistics conditions.
"""

from datetime import datetime


def get_traffic_level(hour: int = None, day_of_week: int = None) -> dict:
    """
    Returns traffic info:
    {level: 'Low'|'Medium'|'High', reason: str, hour: int, day_of_week: int}
    """
    now = datetime.now()
    if hour is None:
        hour = now.hour
    if day_of_week is None:
        day_of_week = now.weekday()  # 0=Monday … 6=Sunday

    is_weekend = day_of_week >= 5  # Saturday or Sunday

    # ── Weekend patterns ───────────────────────────────────
    if is_weekend:
        if 10 <= hour <= 20:
            level, reason = "Medium", "Weekend leisure & shopping traffic"
        elif 20 <= hour <= 22:
            level, reason = "Medium", "Weekend evening outing traffic"
        else:
            level, reason = "Low", "Off-peak weekend hours"

    # ── Weekday patterns ───────────────────────────────────
    elif 7 <= hour <= 9:
        level, reason = "High", "Morning peak rush (7–9 AM)"
    elif 17 <= hour <= 20:
        level, reason = "High", "Evening peak rush (5–8 PM)"
    elif 10 <= hour <= 16:
        level, reason = "Medium", "Moderate daytime traffic"
    elif 21 <= hour <= 23:
        level, reason = "Low", "Late-night light traffic"
    else:
        level, reason = "Low", "Off-peak hours (early morning/night)"

    # Monday extra congestion
    if day_of_week == 0 and "High" not in level:
        reason += " (Monday surge)"

    return {
        "level": level,
        "reason": reason,
        "hour": hour,
        "day_of_week": day_of_week,
        "is_weekend": is_weekend,
    }
