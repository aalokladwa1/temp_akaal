"""Tests: Resilience Platform — EnterpriseResiliencePlatformV5 Facade and End-to-End Run."""

import pytest
from akaal.resilience_eng.facade.platform5 import EnterpriseResiliencePlatformV5
from akaal.resilience_eng.core.config import ResilienceEngConfig, ResilienceEngProfile


class TestEnterpriseResiliencePlatformV5Facade:
    def test_platform_name(self):
        p = EnterpriseResiliencePlatformV5()
        assert p.platform_name == "EnterpriseResiliencePlatformV5"

    def test_version(self):
        p = EnterpriseResiliencePlatformV5()
        assert p.version == "5.0.0"

    def test_profile_default(self):
        p = EnterpriseResiliencePlatformV5()
        assert p.profile == "ENTERPRISE"

    def test_get_platform_health(self):
        p = EnterpriseResiliencePlatformV5()
        health = p.get_platform_health()
        assert health["platform5_status"] == "HEALTHY"
        assert health["all_subsystems_healthy"] is True

    def test_get_observability_metrics(self):
        p = EnterpriseResiliencePlatformV5()
        metrics = p.get_observability_metrics()
        assert metrics["sla_compliance_pct"] == 100.0

    def test_get_experiment_library(self):
        p = EnterpriseResiliencePlatformV5()
        templates = p.get_experiment_library()
        assert len(templates) == 12
        assert "Regional Outage" in templates

    def test_get_maturity_assessment(self):
        p = EnterpriseResiliencePlatformV5()
        mat = p.get_maturity_assessment()
        assert mat["overall_maturity_level"] == "OPTIMIZED_LEVEL_5"
        assert len(mat["recommendations"]) >= 1

    def test_run_resilience_validation_end_to_end(self):
        """Full end-to-end pipeline execution test."""
        p = EnterpriseResiliencePlatformV5()
        result = p.run_resilience_validation()
        assert result["is_successful"] is True
        assert result["domain_results_count"] == 6
        assert result["total_actions_executed"] > 20
        assert result["maturity_level"] == "OPTIMIZED_LEVEL_5"
        assert result["events_published"] > 10
        assert result["report_suite"]["executive_report"]["report_type"] == "EXECUTIVE_SUMMARY"

    def test_custom_profile_config(self):
        config = ResilienceEngConfig(profile=ResilienceEngProfile.FINANCE)
        p = EnterpriseResiliencePlatformV5(config=config, profile=ResilienceEngProfile.FINANCE)
        assert p.profile == "FINANCE"
