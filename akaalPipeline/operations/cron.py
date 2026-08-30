"""akaalPipeline.operations.cron
==============================
Deterministic 5-field cron expression parser, IANA & standard timezone normalizer, and next-occurrence calculator.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone, tzinfo
from typing import Dict, List, Optional, Set, Tuple
import zoneinfo

from akaalPipeline.contracts.errors import PipelineError, PipelineErrorCode

# Standard common timezone offset table (hours, minutes) for environments without system tzdata
_KNOWN_TIMEZONE_OFFSETS: Dict[str, Tuple[int, int]] = {
    "UTC": (0, 0),
    "GMT": (0, 0),
    "Z": (0, 0),
    "ETC/UTC": (0, 0),
    "ETC/GMT": (0, 0),
    "AMERICA/NEW_YORK": (-5, 0),
    "AMERICA/CHICAGO": (-6, 0),
    "AMERICA/DENVER": (-7, 0),
    "AMERICA/LOS_ANGELES": (-8, 0),
    "EUROPE/LONDON": (0, 0),
    "EUROPE/PARIS": (1, 0),
    "EUROPE/BERLIN": (1, 0),
    "ASIA/KOLKATA": (5, 30),
    "ASIA/CALCUTTA": (5, 30),
    "ASIA/TOKYO": (9, 0),
    "ASIA/SINGAPORE": (8, 0),
    "AUSTRALIA/SYDNEY": (10, 0),
}


def validate_timezone(tz_name: str) -> tzinfo:
    """Validate IANA / standard timezone string and return a timezone/ZoneInfo object. Fails closed on invalid timezone."""
    if not tz_name or not isinstance(tz_name, str):
        raise PipelineError(PipelineErrorCode.INVALID_REQUEST, "Timezone string must be a non-empty string.")

    cleaned = tz_name.strip()
    upper_cleaned = cleaned.upper()

    # 1. UTC / GMT direct match
    if upper_cleaned in ("UTC", "GMT", "Z", "ETC/UTC", "ETC/GMT"):
        return timezone.utc

    # 2. Offset strings like UTC+05:30, UTC-04:00, +05:30, -04:00
    offset_match = re.match(r"^(?:UTC|GMT)?([+-])(\d{1,2})(?::?(\d{2}))?$", upper_cleaned)
    if offset_match:
        sign, hrs_str, mins_str = offset_match.groups()
        hrs = int(hrs_str)
        mins = int(mins_str or 0)
        if hrs > 23 or mins > 59:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Timezone offset out of range: {tz_name!r}")
        delta = timedelta(hours=hrs, minutes=mins)
        if sign == "-":
            delta = -delta
        return timezone(delta, name=cleaned)

    # 3. Try zoneinfo.ZoneInfo
    try:
        return zoneinfo.ZoneInfo(cleaned)
    except Exception:
        # Fallback to known standard timezone dictionary for platform portability
        if upper_cleaned in _KNOWN_TIMEZONE_OFFSETS:
            h, m = _KNOWN_TIMEZONE_OFFSETS[upper_cleaned]
            delta = timedelta(hours=h, minutes=m) if h >= 0 else timedelta(hours=h, minutes=-m)
            return timezone(delta, name=cleaned)

    raise PipelineError(
        PipelineErrorCode.INVALID_REQUEST,
        f"Invalid or unrecognized timezone identifier: {tz_name!r}.",
    )


def _parse_field(field_str: str, min_val: int, max_val: int, field_name: str) -> Set[int]:
    """Parse a single cron field with support for *, */step, ranges (a-b), lists (a,b), and combinations."""
    field_str = field_str.strip()
    if not field_str:
        raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Empty cron field for {field_name}.")

    allowed_values: Set[int] = set()

    for part in field_str.split(","):
        part = part.strip()
        if not part:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Invalid empty sub-expression in {field_name}.")

        if "/" in part:
            subparts = part.split("/")
            if len(subparts) != 2:
                raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Invalid step expression '{part}' in {field_name}.")
            range_part, step_str = subparts[0].strip(), subparts[1].strip()
            if not step_str.isdigit() or int(step_str) <= 0:
                raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Invalid step value '{step_str}' in {field_name}.")
            step = int(step_str)

            if range_part == "*":
                start, end = min_val, max_val
            elif "-" in range_part:
                r_parts = range_part.split("-")
                if len(r_parts) != 2 or not r_parts[0].isdigit() or not r_parts[1].isdigit():
                    raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Invalid range '{range_part}' in {field_name}.")
                start, end = int(r_parts[0]), int(r_parts[1])
            elif range_part.isdigit():
                start, end = int(range_part), max_val
            else:
                raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Invalid range expression '{range_part}' in {field_name}.")

            if start < min_val or end > max_val or start > end:
                raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Range [{start}, {end}] out of bounds [{min_val}, {max_val}] for {field_name}.")

            for v in range(start, end + 1, step):
                allowed_values.add(v)

        elif "-" in part:
            r_parts = part.split("-")
            if len(r_parts) != 2 or not r_parts[0].isdigit() or not r_parts[1].isdigit():
                raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Invalid range '{part}' in {field_name}.")
            start, end = int(r_parts[0]), int(r_parts[1])
            if start < min_val or end > max_val or start > end:
                raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Range [{start}, {end}] out of bounds [{min_val}, {max_val}] for {field_name}.")
            for v in range(start, end + 1):
                allowed_values.add(v)

        elif part == "*":
            for v in range(min_val, max_val + 1):
                allowed_values.add(v)

        elif part.isdigit():
            val = int(part)
            if field_name == "day_of_week" and val == 7:
                val = 0
            if val < min_val or val > max_val:
                raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Value {val} out of bounds [{min_val}, {max_val}] for {field_name}.")
            allowed_values.add(val)

        else:
            raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"Unrecognized cron syntax '{part}' in {field_name}.")

    if not allowed_values:
        raise PipelineError(PipelineErrorCode.INVALID_REQUEST, f"No valid values resolved for cron field {field_name}.")

    return allowed_values


class ParsedCronExpression:
    def __init__(self, raw_expression: str) -> None:
        self.raw_expression = raw_expression.strip()
        fields = self.raw_expression.split()
        if len(fields) != 5:
            raise PipelineError(
                PipelineErrorCode.INVALID_REQUEST,
                f"Cron expression must contain exactly 5 fields (minute hour day month day_of_week), got {len(fields)} fields: {raw_expression!r}",
            )
        self.minutes = _parse_field(fields[0], 0, 59, "minute")
        self.hours = _parse_field(fields[1], 0, 23, "hour")
        self.days_of_month = _parse_field(fields[2], 1, 31, "day_of_month")
        self.months = _parse_field(fields[3], 1, 12, "month")
        self.days_of_week = _parse_field(fields[4], 0, 6, "day_of_week")

    def matches(self, dt: datetime) -> bool:
        """Check if local datetime dt matches the cron criteria."""
        if dt.minute not in self.minutes:
            return False
        if dt.hour not in self.hours:
            return False
        if dt.month not in self.months:
            return False
        if dt.day not in self.days_of_month:
            return False

        # Convert Python dt.weekday() (Monday=0..Sunday=6) to standard cron (Sunday=0..Saturday=6)
        cron_dow = (dt.weekday() + 1) % 7
        if cron_dow not in self.days_of_week:
            return False

        return True


def validate_cron_expression(expr: str) -> None:
    """Validate 5-field cron expression syntax and field boundaries."""
    ParsedCronExpression(expr)


def compute_next_occurrence(
    cron_expr: str,
    tz_name: str = "UTC",
    after_utc: datetime | None = None,
    max_search_minutes: int = 525600 * 5,  # 5 years max
) -> str:
    """Compute the next occurrence instant as a normalized ISO UTC string."""
    parsed = ParsedCronExpression(cron_expr)
    tz = validate_timezone(tz_name)

    if after_utc is None:
        after_utc = datetime.now(timezone.utc)
    elif after_utc.tzinfo is None:
        after_utc = after_utc.replace(tzinfo=timezone.utc)
    else:
        after_utc = after_utc.astimezone(timezone.utc)

    # Start searching from the next whole minute
    current_utc = after_utc.replace(second=0, microsecond=0) + timedelta(minutes=1)
    current_local = current_utc.astimezone(tz)

    for _ in range(max_search_minutes):
        if parsed.matches(current_local):
            utc_dt = current_local.astimezone(timezone.utc)
            return utc_dt.isoformat()

        current_local = current_local + timedelta(minutes=1)

    raise PipelineError(
        PipelineErrorCode.INVALID_REQUEST,
        f"No occurrence found for cron {cron_expr!r} in timezone {tz_name!r} within 5 years.",
    )
