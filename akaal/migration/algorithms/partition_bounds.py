from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, Union
from akaal.migration.models.partition import (
    CanonicalDataType,
    CanonicalScalarValue,
    BoundInclusivity,
    CanonicalDomainStep,
    CanonicalRangeBound,
    CanonicalRangeInterval
)

def shift_value(
    val: CanonicalScalarValue,
    step: CanonicalDomainStep,
    direction: str = "successor"
) -> CanonicalScalarValue:
    """
    Shifts a discrete boundary value to its successor or predecessor.
    Only supports INTEGER, DATE, and DECIMAL (with known scale).
    """
    if direction not in ("successor", "predecessor"):
        raise ValueError("Direction must be successor or predecessor.")

    dt = val.data_type
    if dt == CanonicalDataType.INTEGER:
        step_sz = int(step.step_value) if step.step_value is not None else 1
        new_payload = val.int_val + step_sz if direction == "successor" else val.int_val - step_sz
        return CanonicalScalarValue(data_type=dt, int_val=new_payload)

    elif dt == CanonicalDataType.DATE:
        step_sz = int(step.step_value) if step.step_value is not None else 1
        delta = timedelta(days=step_sz)
        new_payload = val.date_val + delta if direction == "successor" else val.date_val - delta
        return CanonicalScalarValue(data_type=dt, date_val=new_payload)

    elif dt == CanonicalDataType.DECIMAL:
        if step.source_scale is None:
            raise ValueError("DECIMAL shifting requires a known scale.")
        step_sz = Decimal(step.step_value) if step.step_value is not None else Decimal(10) ** -step.source_scale
        new_payload = val.decimal_val + step_sz if direction == "successor" else val.decimal_val - step_sz
        return CanonicalScalarValue(data_type=dt, decimal_val=new_payload, scale=step.source_scale)

    else:
        raise ValueError(f"Shifting not supported for type: {dt}")

def normalize_interval(
    interval: CanonicalRangeInterval,
    key_type: CanonicalDataType,
    step: Optional[CanonicalDomainStep] = None
) -> CanonicalRangeInterval:
    """
    Translates intervals with different inclusivity semantics (e.g. Range Left, Range Right)
    to a standard [lower_inclusive, upper_exclusive) interval representation.
    """
    # 1. Lower boundary normalization
    lower_bound = interval.lower
    if not lower_bound.unbounded and lower_bound.inclusivity == BoundInclusivity.EXCLUSIVE:
        if step is None or step.value_type != key_type:
            raise ValueError(f"Exclusive lower boundary translation requires domain step for {key_type}")
        new_vals = tuple(shift_value(v, step, "successor") for v in lower_bound.values)
        normalized_lower = CanonicalRangeBound(values=new_vals, inclusivity=BoundInclusivity.INCLUSIVE, unbounded=False)
    else:
        normalized_lower = lower_bound

    # 2. Upper boundary normalization
    upper_bound = interval.upper
    if not upper_bound.unbounded and upper_bound.inclusivity == BoundInclusivity.INCLUSIVE:
        if step is None or step.value_type != key_type:
            raise ValueError(f"Inclusive upper boundary translation requires domain step for {key_type}")
        new_vals = tuple(shift_value(v, step, "successor") for v in upper_bound.values)
        normalized_upper = CanonicalRangeBound(values=new_vals, inclusivity=BoundInclusivity.EXCLUSIVE, unbounded=False)
    else:
        normalized_upper = upper_bound

    return CanonicalRangeInterval(lower=normalized_lower, upper=normalized_upper)
