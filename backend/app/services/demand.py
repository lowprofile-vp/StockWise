"""Demand series built from plain (date, quantity) events.

Calendar days with no sales or consumption contribute zero. That keeps a
quiet day from disappearing out of the average.
"""

from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from app.algorithms.sliding_window import window_average
from app.services.planning import quantize_qty, to_decimal


def build_daily_totals(events, start_date, end_date):
    totals = {}
    for day, quantity in events:
        if start_date <= day <= end_date:
            totals[day] = totals.get(day, Decimal("0")) + to_decimal(quantity)
    series = []
    day = start_date
    while day <= end_date:
        series.append(totals.get(day, Decimal("0")))
        day += timedelta(days=1)
    return series


def choose_demand(series):
    observed = len(series)
    if observed == 0:
        return {
            "average_7_day": Decimal("0"),
            "average_30_day": None,
            "average_daily_demand": Decimal("0"),
            "observed_days": 0,
            "insufficient_history": True,
        }
    total = sum(series, Decimal("0"))
    average_all = total / Decimal(observed)
    average_7 = window_average(series, 7)
    average_30 = window_average(series, 30) if observed >= 30 else None
    chosen = average_7 if observed >= 7 and average_7 is not None else average_all
    return {
        "average_7_day": quantize_qty(average_7 or 0),
        "average_30_day": quantize_qty(average_30) if average_30 is not None else None,
        "average_daily_demand": quantize_qty(chosen),
        "observed_days": observed,
        "insufficient_history": observed < 7,
    }


def compare_periods(series, window=7):
    """Compare the latest window with the window immediately before it."""
    if len(series) < window * 2:
        return {
            "sufficient": False,
            "trend": "unknown",
            "change_percent": None,
            "recent_average": None,
            "previous_average": None,
        }
    recent = series[-window:]
    previous = series[-2 * window : -window]
    recent_average = sum(recent, Decimal("0")) / Decimal(window)
    previous_average = sum(previous, Decimal("0")) / Decimal(window)
    if previous_average == 0:
        change = None if recent_average > 0 else Decimal("0")
        trend = "increasing" if recent_average > 0 else "stable"
    else:
        change = ((recent_average - previous_average) / previous_average) * Decimal("100")
        change = change.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        if change >= 15:
            trend = "increasing"
        elif change <= -15:
            trend = "declining"
        else:
            trend = "stable"
    return {
        "sufficient": True,
        "trend": trend,
        "change_percent": change,
        "recent_average": quantize_qty(recent_average),
        "previous_average": quantize_qty(previous_average),
    }
