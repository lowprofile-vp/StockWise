"""JSON field parsing. Routes use these so validation messages stay consistent."""

import re
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation

from flask import request

from app.errors import APIError

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise APIError("Request body must be a JSON object.")
    return data


def clean_text(value, field, *, minimum=1, maximum=150, required=True):
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise APIError(f"{field} is required.")
        return None
    if not isinstance(value, str):
        raise APIError(f"{field} must be text.")
    text = " ".join(value.split())
    if len(text) < minimum:
        raise APIError(f"{field} must be at least {minimum} characters.")
    if len(text) > maximum:
        raise APIError(f"{field} must be at most {maximum} characters.")
    return text


def parse_email(value):
    email = clean_text(value, "Email", maximum=255).lower()
    if not EMAIL_RE.match(email):
        raise APIError("Enter a valid email address.")
    return email


def parse_password(value):
    if not isinstance(value, str) or len(value) < 8:
        raise APIError("Password must be at least 8 characters.")
    if len(value) > 128:
        raise APIError("Password is too long.")
    if not any(character.isalpha() for character in value) or not any(character.isdigit() for character in value):
        raise APIError("Password must include a letter and a number.")
    return value


def parse_decimal(value, field, *, minimum=None, maximum=None, allow_zero=True):
    if value is None or value == "":
        raise APIError(f"{field} is required.")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise APIError(f"{field} must be a number.") from exc
    if not number.is_finite():
        raise APIError(f"{field} must be a number.")
    if minimum is not None and number < Decimal(str(minimum)):
        raise APIError(f"{field} must be at least {minimum}.")
    if not allow_zero and number == 0:
        raise APIError(f"{field} must be greater than zero.")
    if maximum is not None and number > Decimal(str(maximum)):
        raise APIError(f"{field} must be at most {maximum}.")
    return number


def parse_int(value, field, *, minimum=None, maximum=None, default=None):
    if value is None or value == "":
        if default is not None:
            return default
        raise APIError(f"{field} is required.")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise APIError(f"{field} must be a whole number.") from exc
    if minimum is not None and number < minimum:
        raise APIError(f"{field} must be at least {minimum}.")
    if maximum is not None and number > maximum:
        raise APIError(f"{field} must be at most {maximum}.")
    return number


def parse_date(value, field="Date", required=False):
    if value is None or value == "":
        if required:
            raise APIError(f"{field} is required.")
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value).strip()
    if "T" in text:
        text = text.split("T", 1)[0]
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except ValueError as exc:
        raise APIError(f"{field} must use the YYYY-MM-DD format.") from exc


def parse_datetime(value, field="Date"):
    """Return a timezone-aware UTC datetime. Date-only values use 12:00 UTC."""
    if value is None or value == "":
        from app.models import utcnow

        return utcnow()
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    text = str(value).strip().replace("Z", "")
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    day = parse_date(text, field, required=True)
    return datetime.combine(day, time(12, 0), tzinfo=timezone.utc)


def as_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.date()
        return value.astimezone(timezone.utc).date()
    if isinstance(value, date):
        return value
    return value


def date_start(day):
    return datetime.combine(day, time.min, tzinfo=timezone.utc)


def date_end(day):
    return datetime.combine(day, time.max, tzinfo=timezone.utc)


def future_limit(moment, field="Date"):
    """Reject dates more than one day ahead of the local calendar."""
    if as_date(moment) > date.today() + timedelta(days=1):
        raise APIError(f"{field} cannot be in the future.")
    return moment
