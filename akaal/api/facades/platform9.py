"""
Platform 9 Public Façade — Reliability Intelligence Integration.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import datetime

from akaal.api.contracts.dto import CapabilityDTO
from akaal.api.contracts.errors import FacadeError
from akaal.api.facades.base import IFacade
from akaal.reliability_intelligence.facade.platform9 import ReliabilityIntelligencePlatformV9


class IPlatform9Facade(IFacade, ABC):
    """Abstract Interface for Platform 9 Reliability Intelligence Façade."""

    @abstractmethod
    async def evaluate_regression(self, target_name: str, baseline_p99_ms: float, current_p99_ms: float) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def detect_drift(self, target_name: str, baseline_p99_ms: float, current_p99_ms: float) -> Dict[str, Any]:
        pass


class Platform9Facade(IPlatform9Facade):
    """Production Platform 9 Façade Implementation routing to ReliabilityIntelligencePlatformV9."""

    def __init__(self, platform_engine: Optional[ReliabilityIntelligencePlatformV9] = None) -> None:
        self._engine = platform_engine or ReliabilityIntelligencePlatformV9()

    async def get_capabilities(self) -> CapabilityDTO:
        return CapabilityDTO(
            platform_name="Platform 9 (Reliability Intelligence Platform)",
            version="9.0.0",
            supported_features=[
                "reliability_regression_testing",
                "reliability_baseline_comparison",
                "reliability_trend_analysis",
                "reliability_drift_detection",
                "reliability_recommendation_engine",
            ],
            active_protocols=["REST", "gRPC"],
        )

    async def evaluate_regression(self, target_name: str, baseline_p99_ms: float, current_p99_ms: float) -> Dict[str, Any]:
        try:
            report = self._engine.evaluate_regression(target_name, baseline_p99_ms, current_p99_ms)
            return {
                "report_id": report.report_id,
                "target_name": report.target_name,
                "status": report.status.value,
                "regressions_found": report.regressions_found,
                "evaluated_at": report.evaluated_at,
            }
        except Exception as e:
            raise FacadeError(f"Platform 9 Regression Evaluation failed: {str(e)}")

    async def detect_drift(self, target_name: str, baseline_p99_ms: float, current_p99_ms: float) -> Dict[str, Any]:
        try:
            report = self._engine.detect_drift(target_name, baseline_p99_ms, current_p99_ms)
            return {
                "report_id": report.report_id,
                "target_name": report.target_name,
                "drift_severity": report.drift_severity.value,
                "baseline_p99_ms": report.baseline_p99_ms,
                "current_p99_ms": report.current_p99_ms,
                "latency_delta_pct": report.latency_delta_pct,
                "detected_at": report.detected_at,
            }
        except Exception as e:
            raise FacadeError(f"Platform 9 Drift Detection failed: {str(e)}")
