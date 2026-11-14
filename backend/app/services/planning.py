"""Pure restocking formulas.

These functions do not touch the database. Services load stock, demand,
and supplier lead time, then call assess_product. Simulations call the
same function with hypothetical inputs.

Safety stock is average daily demand multiplied by SAFETY_DAYS (2).
The review cycle is REVIEW_DAYS (7): how often a manager is expected to
place the next order.

    reorder point = daily demand × lead time + daily demand × safety days
    order-up-to   = daily demand × (lead time + review days + safety days)
    suggested qty = max(0, order-up-to − current stock)

Economic order quantity is not used. It needs a holding cost and a fixed
ordering cost, which this system does not collect. The order-up-to level
is explainable from lead time and the review cycle alone.

Urgency bands, evaluated in this order:

- Critical: stock is zero, or days until stockout <= supplier lead time.
  The product can run out before the next delivery arrives.
- High: days until stockout <= lead time + safety days.
  Lead time is covered, but the safety buffer is already in use.
  This is the "approaching reorder point" band.
- Medium: stock is at or below the minimum threshold, or days until
  stockout <= 3 × lead time.
- Low: none of the above.

Days until stockout = current stock / average daily demand.
A rising 7-day trend adds a small score bump so it ranks earlier inside
the same band. The band itself stays tied to cover versus lead time.
"""

from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

SAFETY_DAYS = 2
REVIEW_DAYS = 7
DEFAULT_LEAD_DAYS = 3
INTEGER_UNITS = {"pcs", "pack", "loaf", "dozen", "bottle", "box", "unit", "piece", "pieces"}


def formula_documentation():
    return {
        "average_daily_demand": (
            "Mean of daily sales plus kitchen consumption over the latest 7 calendar days. "
            "Days with no movement count as zero. With fewer than 7 days of history, the "
            "available days are averaged and the result is marked as a weak estimate. "
            "A 30-day average is reported only when 30 days exist."
        ),
        "days_until_stockout": "current stock ÷ average daily demand",
        "reorder_point": "average daily demand × supplier lead time + average daily demand × 2 safety days",
        "order_up_to_level": "average daily demand × (lead time + 7 review days + 2 safety days)",
        "suggested_quantity": (
            "max(0, order-up-to level − current stock), then raised to the supplier minimum "
            "order quantity when that minimum is larger."
        ),
        "urgency": (
            "Critical when the product is out of stock or days until stockout is within the "
            "supplier lead time. High when cover reaches only the lead time plus the 2-day "
            "safety buffer. Medium when stock is at or below the minimum, or cover is within "
            "three lead times. Otherwise Low."
        ),
        "greedy": "Rank lots by urgency score ÷ cost and take a lot while its full cost fits.",
        "knapsack": (
            "0/1 knapsack. Weight is the lot cost in whole currency units. Value is the "
            "urgency score. The dynamic program maximizes total score within the budget."
        ),
        "estimate_warning": "These figures are estimates from recent usage, not guaranteed future demand.",
    }


def to_decimal(value):
    if isinstance(value, Decimal):
        return value
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def quantize_qty(value):
    return to_decimal(value).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def quantize_money(value):
    return to_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def round_qty(quantity, unit):
    quantity = to_decimal(quantity)
    if quantity <= 0:
        return Decimal("0")
    if unit and str(unit).strip().lower() in INTEGER_UNITS:
        return quantity.quantize(Decimal("1"), rounding=ROUND_CEILING)
    return quantity.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def format_days(days):
    if days is None:
        return "an unknown number of"
    number = to_decimal(days)
    if number == number.to_integral_value():
        whole = int(number)
        return f"{whole} day" if whole == 1 else f"{whole} days"
    return f"{number.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)} days"


def stock_status(stock, minimum, days, lead_time_days):
    stock = to_decimal(stock)
    minimum = to_decimal(minimum)
    if stock <= 0:
        return "Out of Stock"
    if days is not None and to_decimal(days) <= Decimal(int(lead_time_days)):
        return "Critical"
    if minimum > 0 and stock <= (minimum * Decimal("0.5")):
        return "Critical"
    if stock <= minimum:
        return "Low Stock"
    return "Healthy"


def assess_product(
    *,
    current_stock,
    daily_demand,
    lead_time_days,
    minimum_stock,
    purchase_price,
    unit,
    minimum_order_quantity=0,
    trend="unknown",
    today=None,
):
    stock = quantize_qty(current_stock)
    daily = quantize_qty(daily_demand)
    if daily < 0:
        daily = Decimal("0")
    lead = max(0, int(lead_time_days))
    minimum = quantize_qty(minimum_stock)
    price = quantize_money(purchase_price)
    moq = quantize_qty(minimum_order_quantity)
    today = today or date.today()

    if daily > 0:
        reorder = quantize_qty(daily * (Decimal(lead) + Decimal(SAFETY_DAYS)))
        order_up_to = quantize_qty(daily * Decimal(lead + REVIEW_DAYS + SAFETY_DAYS))
        days = (stock / daily).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        reorder = minimum
        order_up_to = minimum
        days = Decimal("0.00") if stock <= 0 else None

    suggested = round_qty(max(Decimal("0"), order_up_to - stock), unit)
    if moq > 0 and Decimal("0") < suggested < moq:
        suggested = round_qty(moq, unit)
    cost = quantize_money(suggested * price)

    if days is None:
        gap = None
        stockout = None
    else:
        gap = (days - Decimal(lead)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        stockout = today if stock <= 0 else today + timedelta(days=max(0, int(days.to_integral_value(rounding=ROUND_CEILING))))

    level, score, reason = _classify(stock, daily, days, lead, minimum, reorder, unit)
    score, reason = _apply_trend(level, score, reason, trend)

    return {
        "days_until_stockout": days,
        "stockout_date": stockout,
        "reorder_point": reorder,
        "order_up_to": order_up_to,
        "suggested_quantity": suggested,
        "estimated_cost": cost,
        "urgency": level,
        "urgency_score": round(score, 1),
        "stock_status": stock_status(stock, minimum, days, lead),
        "reason": reason,
        "priority_gap_days": gap,
        "safety_days": SAFETY_DAYS,
        "review_days": REVIEW_DAYS,
    }


def _classify(stock, daily, days, lead, minimum, reorder, unit):
    if stock <= 0:
        return  (
            "Critical",
            100.0,
            "The product is out of stock, so a delivery is already late relative to demand.",
        )
    if daily <= 0:
        if stock <= minimum:
            return (
                "Medium",
                35.0,
                "There is not enough recent demand to estimate a stockout date, and the quantity is at or below the minimum threshold.",
            )
        return (
            "Low",
            8.0,
            "No measurable sales or consumption were recorded in the observation window.",
        )
    if days <= Decimal(lead):
        ratio = float(days / Decimal(lead)) if lead > 0 else 0.0
        ratio = min(max(ratio, 0.0), 1.0)
        score = 80 + 20 * (1 - ratio)
        if lead == 0 or days < Decimal(lead):
            timing = "before a supplier delivery can arrive"
        else:
            timing = "on the day a supplier delivery is due, with no safety buffer left"
        return (
            "Critical",
            score,
            f"Estimated to run out in {format_days(days)}, {timing} ({lead}-day lead time).",
        )
    safety_limit = Decimal(lead + SAFETY_DAYS)
    if days <= safety_limit:
        span = SAFETY_DAYS if SAFETY_DAYS else 1
        position = float(days - Decimal(lead)) / span
        position = min(max(position, 0.0), 1.0)
        score = 70 - 15 * position
        return (
            "High",
            score,
            (
                f"Stock lasts about {format_days(days)}. That covers the {lead}-day lead time "
                f"but not the {SAFETY_DAYS}-day safety buffer. Reorder point: {_fmt_qty(reorder, unit)}."
            ),
        )
    below_minimum = stock <= minimum
    within_horizon = days <= Decimal(lead * 3 if lead else REVIEW_DAYS)
    if below_minimum or within_horizon:
        if below_minimum and within_horizon:
            score = 46.0
            reason = "Quantity is at or below the minimum threshold, and cover is within three supplier lead times."
        elif below_minimum:
            score = 40.0
            reason = "Quantity is at or below the minimum stock threshold."
        else:
            score = 34.0
            horizon = lead * 3 if lead else REVIEW_DAYS
            reason = f"Cover of {format_days(days)} is within {horizon} days (three lead times)."
        return "Medium", score, reason
    return (
        "Low",
        15.0,
        "Stock covers demand beyond the reorder point and the minimum threshold.",
    )


def _apply_trend(level, score, reason, trend):
    if trend == "increasing":
        bump = 3 if level == "Critical" else 8
        score = min(100.0, score + bump)
        reason = f"{reason} Recent demand is higher than the previous period."
    elif trend == "declining" and level == "Critical":
        reason = (
            f"{reason} Recent demand is lower than the previous period, "
            "but a stockout can still arrive before the next delivery."
        )
    elif trend == "declining" and level == "High":
        score = max(50.0, score - 4)
        reason = f"{reason} Recent demand is lower than the previous period."
    elif trend == "declining" and level == "Low":
        score = max(1.0, score - 4)
        reason = f"{reason} Recent demand is lower than the previous period."
    return score, reason


def _fmt_qty(quantity, unit):
    number = quantize_qty(quantity)
    text = format(number.normalize(), "f")
    return f"{text} {unit}".strip()


def rank_key(metric, index):
    """Lower tuple = more urgent. Used as the min-heap priority."""
    days = metric.get("days_until_stockout")
    days_key = Decimal("9999") if days is None else to_decimal(days)
    score = float(metric.get("urgency_score") or 0)
    return (-score, days_key, index)
