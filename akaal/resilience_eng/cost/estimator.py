"""Experiment Cost Estimator and Operational Cost Forecast."""

from typing import Dict, Any


class OperationalCostForecaster:
    def forecast_cost(self, duration_sec: float, worker_count: int) -> Dict[str, Any]:
        return {
            "estimated_cpu_hours": round((duration_sec / 3600.0) * worker_count * 2, 4),
            "estimated_memory_gb_hours": round((duration_sec / 3600.0) * worker_count * 4, 4),
            "estimated_downtime_risk": "ZERO_DOWNTIME",
            "estimated_cost_usd": 0.05,
        }


class ExperimentCostEstimator:
    """Estimates resource usage and operational cost before execution."""

    def __init__(self):
        self.forecaster = OperationalCostForecaster()

    def estimate_experiment_cost(self, duration_sec: float = 60.0, worker_count: int = 4) -> Dict[str, Any]:
        return self.forecaster.forecast_cost(duration_sec, worker_count)
