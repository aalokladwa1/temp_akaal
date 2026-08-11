"""AKAAL Evidence-Based Preflight and Runtime Adaptive EWMA ETA Engine."""

import math
import datetime
from typing import Dict, Any, Optional

# Algorithm Configuration Constants
DEFAULT_EWMA_ALPHA = 0.3  # EWMA smoothing weight parameter (Configuration/Algorithm Parameter)

class ETAEngine:
    """Calculates preflight evidence-based ETA and runtime adaptive EWMA ETA."""

    @staticmethod
    def calculate_preflight_eta(
        selected_objects: list,
        source_read_rows_per_sec: Optional[float] = None,
        target_write_rows_per_sec: Optional[float] = None,
        parallelism: int = 1,
        has_catalog_stats: bool = True
    ) -> Dict[str, Any]:
        """Calculates evidence-based ETA before migration transport execution with accurate state semantics."""
        total_rows = 0
        total_bytes = 0
        table_count = 0

        stats_sources = set()
        for obj in selected_objects:
            if isinstance(obj, dict):
                o_type = str(obj.get("object_type", "Table")).upper()
                if o_type in ("TABLE", "CANONICALTABLE"):
                    r_val = (
                        obj.get("estimated_rows") or
                        obj.get("row_count") or
                        obj.get("num_rows") or
                        obj.get("numRows") or
                        obj.get("rowCount") or
                        obj.get("estimated_row_count") or
                        0
                    )
                    b_val = (
                        obj.get("estimated_bytes") or
                        obj.get("bytes") or
                        obj.get("size_bytes") or
                        obj.get("data_length") or
                        (float(obj.get("estimated_size_gb") or 0) * (1024 ** 3)) or
                        0
                    )
                    total_rows += int(r_val or 0)
                    total_bytes += int(b_val or 0)
                    table_count += 1
                    if obj.get("statistics_source"):
                        stats_sources.add(obj.get("statistics_source"))
            elif hasattr(obj, "estimated_rows"):
                total_rows += getattr(obj, "estimated_rows", 0) or 0
                table_count += 1

        primary_stats_source = ", ".join(sorted(stats_sources)) if stats_sources else "oracle_catalog"

        has_source_bench = source_read_rows_per_sec is not None and source_read_rows_per_sec > 0
        has_target_bench = target_write_rows_per_sec is not None and target_write_rows_per_sec > 0

        # State A: BENCHMARKS_UNAVAILABLE
        if not has_source_bench and not has_target_bench:
            return {
                "estimated_duration_seconds": None,
                "estimated_duration_display": "Not yet estimated",
                "eta_confidence": "Low",
                "eta_basis": "Awaiting physical connection benchmark measurements",
                "source_read_benchmark": None,
                "target_write_benchmark": None,
                "estimated_catalog_rows": total_rows,
                "estimated_catalog_bytes": total_bytes,
                "statistics_source": primary_stats_source,
                "eta_state": "BENCHMARKS_UNAVAILABLE"
            }

        # State B: PARTIALLY_MEASURED
        if not has_source_bench or not has_target_bench:
            return {
                "estimated_duration_seconds": None,
                "estimated_duration_display": "Not yet estimated",
                "eta_confidence": "Low",
                "eta_basis": f"Partial connection benchmark measurements (Source: {source_read_rows_per_sec}, Target: {target_write_rows_per_sec})",
                "source_read_benchmark": round(source_read_rows_per_sec, 2) if has_source_bench else None,
                "target_write_benchmark": round(target_write_rows_per_sec, 2) if has_target_bench else None,
                "estimated_catalog_rows": total_rows,
                "estimated_catalog_bytes": total_bytes,
                "statistics_source": primary_stats_source,
                "eta_state": "PARTIALLY_MEASURED"
            }

        # State C: CATALOG_VOLUME_UNAVAILABLE
        if total_rows == 0:
            return {
                "estimated_duration_seconds": None,
                "estimated_duration_display": "Not yet estimated",
                "eta_confidence": "Low",
                "eta_basis": "Physical throughput measured; selected-table catalog row estimates unavailable",
                "source_read_benchmark": round(source_read_rows_per_sec, 2),
                "target_write_benchmark": round(target_write_rows_per_sec, 2),
                "estimated_catalog_rows": 0,
                "estimated_catalog_bytes": 0,
                "statistics_source": primary_stats_source,
                "eta_state": "CATALOG_VOLUME_UNAVAILABLE"
            }

        effective_read_rate = source_read_rows_per_sec
        effective_write_rate = target_write_rows_per_sec
        raw_bottleneck = min(effective_read_rate, effective_write_rate)

        # Microbenchmark extrapolation guard: 100-row microbenchmark completing at timer-resolution floor
        # must NOT be extrapolated directly as 100k rows/sec without low-confidence marking (P0.10-M / Rectification 8)
        if raw_bottleneck > 30000.0:
            bottleneck_rows_per_sec = 25000.0  # Apply conservative floor adjustment
            eta_conf = "ETA_LOW_CONFIDENCE"
            conf_reason = "Microbenchmark timing floor detected; throughput adjusted to conservative baseline"
        else:
            bottleneck_rows_per_sec = raw_bottleneck
            eta_conf = "Medium"
            conf_reason = "Representative single-stream benchmark"

        # Truthful ETA Provenance matching (P0.10-N / Rectification 8)
        if "physical_count" in primary_stats_source:
            basis_text = f"Conservative preflight estimate based on measured throughput ({round(bottleneck_rows_per_sec, 1)} rows/sec) & physical exact source counts"
        else:
            basis_text = f"Conservative preflight estimate based on measured throughput ({round(bottleneck_rows_per_sec, 1)} rows/sec) & Oracle catalog statistics"

        if conf_reason and eta_conf == "ETA_LOW_CONFIDENCE":
            basis_text += f" ({conf_reason})"

        # State E: ETA_AVAILABLE (Both physical benchmarks + non-zero catalog row statistics present)
        conn_est_sec = 2.0
        schema_est_sec = min(30.0, max(2.0, round(table_count / 100.0, 1)))
        transport_sec = total_rows / max(bottleneck_rows_per_sec, 1.0)
        val_est_sec = min(30.0, max(2.0, round(table_count / 200.0, 1)))

        transport_estimated_seconds = math.ceil(transport_sec)
        total_estimated_seconds = math.ceil(conn_est_sec + schema_est_sec + transport_sec + val_est_sec)

        mins = total_estimated_seconds // 60
        secs = total_estimated_seconds % 60
        display_str = f"~{mins}m {secs}s" if mins > 0 else f"~{secs}s"

        return {
            "estimated_duration_seconds": total_estimated_seconds,
            "estimated_duration_display": display_str,
            "eta_confidence": eta_conf,
            "eta_basis": basis_text,
            "source_read_benchmark": round(effective_read_rate, 2),
            "target_write_benchmark": round(effective_write_rate, 2),
            "estimated_catalog_rows": total_rows,
            "estimated_catalog_bytes": total_bytes,
            "statistics_source": primary_stats_source,
            "eta_state": "ETA_AVAILABLE",
            "connection_estimate_seconds": conn_est_sec,
            "schema_estimate_seconds": schema_est_sec,
            "transport_estimate_seconds": round(transport_sec, 2),
            "validation_estimate_seconds": val_est_sec,
            "total_estimate_seconds": total_estimated_seconds
        }

    @staticmethod
    def calculate_runtime_adaptive_eta(
        rows_total: int,
        rows_transferred: int,
        observed_rows_per_sec: float,
        previous_ewma_rate: Optional[float] = None,
        alpha: float = DEFAULT_EWMA_ALPHA
    ) -> Dict[str, Any]:
        """Calculates runtime EWMA stabilized adaptive ETA from actual observed execution."""
        rows_remaining = max(rows_total - rows_transferred, 0)
        
        if observed_rows_per_sec <= 0 and (previous_ewma_rate is None or previous_ewma_rate <= 0):
            return {
                "rows_remaining": rows_remaining,
                "ewma_rows_per_sec": 0.0,
                "estimated_remaining_seconds": None,
                "estimated_completion_time": None,
                "display_eta": "Calibrating..."
            }

        if previous_ewma_rate is None or previous_ewma_rate <= 0:
            ewma_rate = observed_rows_per_sec
        else:
            ewma_rate = (alpha * observed_rows_per_sec) + ((1.0 - alpha) * previous_ewma_rate)

        ewma_rate = max(ewma_rate, 0.1)
        remaining_seconds = math.ceil(rows_remaining / ewma_rate) if rows_remaining > 0 else 0
        completion_instant = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=remaining_seconds)

        mins = remaining_seconds // 60
        secs = remaining_seconds % 60
        display_str = f"{mins}m {secs}s remaining" if mins > 0 else f"{secs}s remaining"

        return {
            "rows_remaining": rows_remaining,
            "ewma_rows_per_sec": round(ewma_rate, 2),
            "estimated_remaining_seconds": remaining_seconds,
            "estimated_completion_time": completion_instant.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "display_eta": display_str
        }
