import re


def normalize_type(raw: str) -> str:
    if not raw:
        raise ValueError("Empty type not allowed")

    t = raw.strip().upper()

    # whitespace collapse
    t = re.sub(r"\s+", " ", t)

    # alias normalization
    t = t.replace("TIMESTAMPTZ", "TIMESTAMP")
    t = t.replace("TIME WITH TIME ZONE", "TIME")
    t = t.replace("TIME WITHOUT TIME ZONE", "TIME")

    return t