"""Deterministic per-datatype value generation (build-spec §8 datatype coverage).

Every function here is a pure function of (column spec, a seeded RNG derived
from table/column/row identity). No wall-clock time, no uuid4() (§29).
"""
from __future__ import annotations

from decimal import Decimal
import datetime as dt

from config.schema_spec import ColType, ColumnSpec

# ---- Unicode phrase pools (build-spec §8: English, Kannada, Devanagari, Arabic,
#      CJK, accented European, currency symbols, emoji, combining characters) ----

UNICODE_POOLS = {
    "en": ["order", "invoice", "customer", "shipment", "warehouse", "signed contract"],
    "kn": ["ನಮಸ್ಕಾರ", "ಗ್ರಾಹಕ", "ಸರಕುಪಟ್ಟಿ", "ಮಳಿಗೆ"],
    "hi": ["नमस्ते", "ग्राहक", "चालान", "गोदाम"],
    "ar": ["مرحبا", "العميل", "الفاتورة", "المستودع"],
    "cjk": ["你好", "顧客", "請求書", "倉庫", "注文"],
    "emoji": ["café €5.00 ✅", "naïve résumé", "€ ¥ £ ₹ ₩", "📦🚚✅", "éclair"],  # includes combining accent
    "mixed": ["Müller & Söhne GmbH", "Café Résumé", "naïve façade", "Grüße", "Zürich"],
}


def unicode_text(rng, profile: str, max_len: int) -> str:
    pool = UNICODE_POOLS.get(profile or "mixed", UNICODE_POOLS["mixed"])
    parts = [rng.choice(pool) for _ in range(rng.randint(1, 3))]
    text = " ".join(parts)
    return text[:max_len] if max_len else text


def ascii_text(rng, max_len: int) -> str:
    words = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel",
             "india", "juliet", "kilo", "lima", "mike", "november", "oscar", "papa"]
    text = " ".join(rng.choice(words) for _ in range(rng.randint(1, 4)))
    return text[:max_len] if max_len else text


def gen_number(rng, col: ColumnSpec):
    return round(rng.uniform(-1_000_000, 1_000_000), 2)


def gen_number_38(rng, col: ColumnSpec) -> str:
    digits = rng.randint(1, 38)
    lo = 0 if digits == 1 else 10 ** (digits - 1)
    hi = (10 ** digits) - 1
    sign = -1 if rng.random() < 0.05 else 1
    return str(sign * rng.randint(lo, hi))


def gen_number_p_s(rng, col: ColumnSpec) -> str:
    precision = col.precision or 10
    scale = col.scale if col.scale is not None else 2
    int_digits = max(1, precision - max(scale, 0))
    magnitude = rng.randint(0, (10 ** int_digits) - 1)
    sign = Decimal(-1) if rng.random() < 0.08 else Decimal(1)
    if scale >= 0:
        frac = rng.randint(0, (10 ** scale) - 1) if scale > 0 else 0
        value = Decimal(magnitude) + (Decimal(frac) / (Decimal(10) ** scale) if scale > 0 else 0)
    else:
        # negative scale: rounding granularity of 10**|scale|
        value = Decimal(magnitude) * (Decimal(10) ** (-scale))
    value = value * sign
    return str(value)


def gen_float(rng, col: ColumnSpec) -> float:
    exp = rng.randint(-12, 12)
    mantissa = rng.uniform(1.0, 9.999999)
    sign = -1 if rng.random() < 0.5 else 1
    return sign * mantissa * (10 ** exp)


def gen_text(rng, col: ColumnSpec) -> str:
    max_len = col.length or 200
    if col.unicode_profile:
        return unicode_text(rng, col.unicode_profile, max_len)
    return ascii_text(rng, max_len)


def gen_date(rng, col: ColumnSpec) -> str:
    special = {
        "leap_day_case": dt.date(2000 + 4 * rng.randint(0, 6), 2, 29),
        "historical_date": dt.date(1850 + rng.randint(0, 40), rng.randint(1, 12), rng.randint(1, 28)),
        "future_date": dt.date(2090 + rng.randint(0, 9), rng.randint(1, 12), rng.randint(1, 28)),
    }
    if col.name in special:
        return special[col.name].isoformat()
    days = rng.randint(0, 45000)  # ~1900-01-01 .. ~2023-ish range from epoch offset below
    base = dt.date(1900, 1, 1)
    return (base + dt.timedelta(days=days)).isoformat()


def gen_timestamp(rng, col: ColumnSpec) -> str:
    base = dt.datetime(1970, 1, 1) + dt.timedelta(seconds=rng.randint(0, 60 * 60 * 24 * 365 * 55))
    micros = rng.randint(0, 999999)
    return base.strftime("%Y-%m-%d %H:%M:%S") + f".{micros:06d}"


def gen_timestamp_tz(rng, col: ColumnSpec) -> str:
    base = gen_timestamp(rng, col)
    offset_minutes = rng.choice([-720, -480, -300, 0, 60, 180, 330, 480, 540])
    sign = "+" if offset_minutes >= 0 else "-"
    offset_minutes = abs(offset_minutes)
    if col.name == "positive_offset":
        sign = "+"
    if col.name == "negative_offset":
        sign = "-"
    return f"{base}{sign}{offset_minutes // 60:02d}:{offset_minutes % 60:02d}"


def gen_interval_ym(rng, col: ColumnSpec) -> str:
    sign = "+" if rng.random() > 0.1 else "-"
    return f"{sign}{rng.randint(0,20):02d}-{rng.randint(0,11):02d}"


def gen_interval_ds(rng, col: ColumnSpec) -> str:
    sign = "+" if rng.random() > 0.1 else "-"
    return (f"{sign}{rng.randint(0,999):03d} {rng.randint(0,23):02d}:{rng.randint(0,59):02d}:"
            f"{rng.randint(0,59):02d}.{rng.randint(0,999999):06d}")


def gen_raw(rng, col: ColumnSpec) -> bytes:
    n = col.length or 16
    if col.name == "zero_bytes":
        return b"\x00" * n
    return bytes(rng.randrange(256) for _ in range(n))


def gen_json(rng, col: ColumnSpec) -> str:
    import json as _json
    payload = {
        "id": rng.randint(1, 10 ** 9),
        "label": unicode_text(rng, "mixed", 40),
        "tags": [ascii_text(rng, 10) for _ in range(rng.randint(0, 3))],
        "active": rng.random() > 0.5,
        "score": round(rng.uniform(0, 100), 3),
    }
    return _json.dumps(payload, ensure_ascii=False)


def gen_xml(rng, col: ColumnSpec) -> str:
    label = unicode_text(rng, "mixed", 40)
    return f'<record id="{rng.randint(1,10**6)}"><label>{label}</label><active>{str(rng.random()>0.5).lower()}</active></record>'


_GENERATORS = {
    ColType.NUMBER: gen_number,
    ColType.NUMBER_38: gen_number_38,
    ColType.NUMBER_P_S: gen_number_p_s,
    ColType.INTEGER: lambda rng, col: rng.randint(0, 2_000_000_000),
    ColType.FLOAT: gen_float,
    ColType.BINARY_FLOAT: gen_float,
    ColType.BINARY_DOUBLE: gen_float,
    ColType.VARCHAR2: gen_text,
    ColType.NVARCHAR2: gen_text,
    ColType.CHAR: gen_text,
    ColType.NCHAR: gen_text,
    ColType.DATE: gen_date,
    ColType.TIMESTAMP: gen_timestamp,
    ColType.TIMESTAMP_TZ: gen_timestamp_tz,
    ColType.TIMESTAMP_LTZ: gen_timestamp_tz,
    ColType.INTERVAL_YM: gen_interval_ym,
    ColType.INTERVAL_DS: gen_interval_ds,
    ColType.RAW: gen_raw,
    ColType.JSON: gen_json,
    ColType.XMLTYPE: gen_xml,
}


def generate_scalar_value(rng, col: ColumnSpec):
    """Generate a value for any non-LOB column type. LOB columns (CLOB/NCLOB/BLOB)
    are handled by generator/lob_factory.py instead."""
    gen = _GENERATORS.get(col.type)
    if gen is None:
        raise ValueError(f"no generator for {col.type}")
    return gen(rng, col)
