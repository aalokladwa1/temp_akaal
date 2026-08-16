"""
AKAAL Engine — Canonical AKAAL-Side Data Filter & Sampling Evaluator.
Provides one unified, type-aware, deterministic row filtering & column projection engine
for connectors where native database source pushdown is partially or wholly unavailable.
"""

import hashlib
from typing import List, Dict, Any, Optional


class AkaalSideFilterEvaluator:
    """
    Canonical AKAAL-side filter, projection, and sampling authority.
    Reused across physical connectors classified as PROVEN_AKAAL_SIDE.
    """

    @staticmethod
    def evaluate_predicate(row: Dict[str, Any], predicate: Dict[str, Any]) -> bool:
        col = predicate.get("column")
        op = str(predicate.get("operator", "=")).upper()
        val = predicate.get("value")

        if not col or col not in row:
            if op == "IS NULL":
                return True
            return False

        r_val = row.get(col)
        if r_val is None:
            return op == "IS NULL"

        if op == "=":
            return r_val == val
        elif op == "!=":
            return r_val != val
        elif op == ">":
            return r_val > val
        elif op == ">=":
            return r_val >= val
        elif op == "<":
            return r_val < val
        elif op == "<=":
            return r_val <= val
        elif op == "IN" and isinstance(val, list):
            return r_val in val
        elif op == "NOT IN" and isinstance(val, list):
            return r_val not in val
        elif op == "LIKE" and isinstance(val, str):
            pattern = val.replace("%", "").lower()
            return pattern in str(r_val).lower()
        elif op == "IS NOT NULL":
            return r_val is not None

        return True

    @classmethod
    def filter_batch(
        cls,
        rows: List[Dict[str, Any]],
        columns: Optional[List[str]] = None,
        predicates: Optional[List[Dict[str, Any]]] = None,
        sampling: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Filters, projects, and samples an incoming row batch deterministically."""
        filtered = []
        for r in rows:
            if not isinstance(r, dict):
                filtered.append(r)
                continue

            # 1. Apply Row Predicates
            match = True
            if predicates:
                for p in predicates:
                    if not cls.evaluate_predicate(r, p):
                        match = False
                        break
            if not match:
                continue

            # 2. Apply Column Projection
            if columns:
                proj_r = {c: r[c] for c in columns if c in r}
                # Preserve unprojected dict fields if empty match to prevent data loss
                if not proj_r:
                    proj_r = dict(r)
            else:
                proj_r = dict(r)

            filtered.append(proj_r)

        # 3. Apply Deterministic Physical Sampling
        if sampling and filtered:
            method = str(sampling.get("method", "NONE")).upper()
            sample_size = float(sampling.get("sample_size", 100.0))

            if method == "FIXED_ROWS":
                limit = int(sample_size)
                filtered = filtered[:limit]
            elif method == "PERCENTAGE":
                rate = max(0.0, min(100.0, sample_size))
                sampled = []
                for r in filtered:
                    # Deterministic hash modulo ordering
                    raw_bytes = str(sorted(r.items())).encode("utf-8")
                    h_val = int(hashlib.md5(raw_bytes).hexdigest()[:8], 16)
                    if (h_val % 100) < rate:
                        sampled.append(r)
                filtered = sampled

        return filtered
