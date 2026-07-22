"""
Akaal Platform 6 - Enterprise Performance Engine Package.
"""

from akaal.performance.failures.classification import PerformanceEngineError, PerformanceFailureType
from akaal.performance.discovery.capability import RuntimeCapabilityDiscovery
from akaal.performance.decision.confidence import ConfidenceEngine, OptimizationConfidence
from akaal.performance.decision.policy_engine import PolicyEngine, EnterprisePolicy
from akaal.performance.decision.rule_engine import RuleEngine, OptimizationRule, Recommendation
from akaal.performance.config.profiles import PerformanceProfiles, PerformanceProfile, FeatureFlag, ProfileType
from akaal.performance.config.reload import ConfigurationHotReloader
from akaal.performance.governor.governor import ResourceGovernor
from akaal.performance.health.score import RuntimeHealthScore
from akaal.performance.facade.runtime import PerformanceRuntimeV1, DefaultPerformanceRuntimeV1
from akaal.performance.verification.architecture import ArchitectureVerifier

__all__ = [
    "PerformanceEngineError",
    "PerformanceFailureType",
    "RuntimeCapabilityDiscovery",
    "ConfidenceEngine",
    "OptimizationConfidence",
    "PolicyEngine",
    "EnterprisePolicy",
    "RuleEngine",
    "OptimizationRule",
    "Recommendation",
    "PerformanceProfiles",
    "PerformanceProfile",
    "FeatureFlag",
    "ProfileType",
    "ConfigurationHotReloader",
    "ResourceGovernor",
    "RuntimeHealthScore",
    "PerformanceRuntimeV1",
    "DefaultPerformanceRuntimeV1",
    "ArchitectureVerifier",
]
