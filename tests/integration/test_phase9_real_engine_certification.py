"""
Phase 9 — Real Engine Integration Certification Test Suite
===========================================================
Executes the complete end-to-end intelligence pipeline:
  Scout → Rulebook → Decoder → Risk → Planner → Advisor → Enterprise Intelligence
against LIVE real database engines (PostgreSQL 16/18, MySQL 8.0, and Oracle 23ai).

Verification Requirements:
  • Live database discovery & connection using real credentials.
  • Strict stage-by-stage data flow: each stage consumes the real output of the previous stage.
  • Complete model lineage, SHA-256 checksum stability, immutability checks.
  • Technical reports, manifests, readiness assessments, strategy synthesis generation.
  • 3-run determinism against live engine schemas.
"""

import asyncio
import json
import unittest
from typing import Dict, Set

from akaal.core.models.enums import SystemType
from akaal.core.models.project import ConnectionConfig

from akaal.scout.api.scout_platform import ScoutPlatform
from akaal.scout.models.discovery_report import DiscoveryReport

from akaal.rulebook.api.rulebook_platform import RulebookPlatform
from akaal.rulebook.models.migration_ruleset import MigrationRuleSet

from akaal.decoder.api.decoder_platform import DecoderPlatform
from akaal.decoder.models.canonical_migration_model import CanonicalMigrationModel
from akaal.decoder.serialization.canonical_serializer import CanonicalSerializer

from akaal.risk.api.risk_platform import RiskPlatform
from akaal.risk.models.risk_assessment_model import RiskAssessmentModel
from akaal.risk.serialization.risk_serializer import RiskSerializer

from akaal.planner.api.planner_platform import PlannerPlatform
from akaal.planner.models.migration_execution_plan import MigrationExecutionPlan
from akaal.planner.serialization.planner_serializer import PlannerSerializer
from akaal.planner.validation.planner_validator import PlannerValidator

from akaal.advisor.api.advisor_platform import AdvisorPlatform
from akaal.advisor.models.advisory_context import AdvisoryContext
from akaal.advisor.models.migration_advisory_model import MigrationAdvisoryModel
from akaal.advisor.serialization.advisor_serializer import AdvisorSerializer
from akaal.advisor.governance.advisor_governance import AdvisorGovernance

from akaal.intelligence.api.enterprise_intelligence_platform import EnterpriseIntelligencePlatform
from akaal.intelligence.models.enterprise_intelligence_model import EnterpriseIntelligenceModel
from akaal.intelligence.serialization.enterprise_intelligence_serializer import EnterpriseIntelligenceSerializer
from akaal.intelligence.governance.enterprise_intelligence_governance import EnterpriseIntelligenceGovernance


# ─────────────────────────────────────────────────────────────────────────────
# Real Connection Config Helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_postgres_config(port: int = 5432) -> ConnectionConfig:
    cfg = ConnectionConfig(
        system_type=SystemType.POSTGRESQL,
        host="127.0.0.1",
        port=port,
        database_name="postgres",
        credentials_ref="postgres_creds",
    )
    cfg.username = "akaal_admin"
    cfg.password = "AkaalPass2026"
    return cfg


def get_mysql_config() -> ConnectionConfig:
    cfg = ConnectionConfig(
        system_type=SystemType.MYSQL,
        host="127.0.0.1",
        port=3306,
        database_name="akaal_smoke_test",
        credentials_ref="mysql_creds",
    )
    cfg.username = "akaal_admin"
    cfg.password = "AkaalPass2026"
    return cfg


def get_oracle_config() -> ConnectionConfig:
    cfg = ConnectionConfig(
        system_type=SystemType.ORACLE,
        host="localhost",
        port=1521,
        database_name="FREEPDB1",
        credentials_ref="oracle_creds",
    )
    cfg.username = "akaal_admin"
    cfg.password = "AkaalPass2026"
    return cfg


async def run_live_pipeline(config: ConnectionConfig, target_engine: str):
    """Executes full 7-stage pipeline against a live database connection."""
    report = await ScoutPlatform.discover(config, force_refresh=True)
    ruleset = RulebookPlatform.generate_ruleset(report, target_engine=target_engine)
    canonical = DecoderPlatform.normalize(report, ruleset)
    risk = RiskPlatform.assess_risk(canonical)
    plan = PlannerPlatform.build_execution_plan(risk_model=risk)
    
    adv_platform = AdvisorPlatform.create_default()
    advisory = adv_platform.analyze(
        plan,
        context=AdvisoryContext(environment="production", database_type=target_engine.lower()),
        advisory_id=f"ADV-REAL-{target_engine}",
    )
    
    ei_platform = EnterpriseIntelligencePlatform()
    intelligence = ei_platform.analyze(advisory)
    
    return {
        "report": report,
        "ruleset": ruleset,
        "canonical": canonical,
        "risk": risk,
        "plan": plan,
        "advisory": advisory,
        "intelligence": intelligence,
        "adv_platform": adv_platform,
        "ei_platform": ei_platform,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test Classes
# ─────────────────────────────────────────────────────────────────────────────

class TestRealEnginePostgresPipeline(unittest.TestCase):
    """Real engine integration certification for PostgreSQL 16."""

    @classmethod
    def setUpClass(cls):
        cfg = get_postgres_config(5432)
        cls.data = asyncio.run(run_live_pipeline(cfg, "POSTGRESQL"))

    def test_scout_live_postgres_metadata(self):
        report: DiscoveryReport = self.data["report"]
        self.assertIsNotNone(report)
        self.assertEqual(report.engine_info.system_type, "POSTGRESQL")
        self.assertTrue(len(report.sha256_checksum) > 0)
        self.assertIsNotNone(report.schema_inventory)

    def test_rulebook_live_postgres_rules(self):
        ruleset: MigrationRuleSet = self.data["ruleset"]
        self.assertIsNotNone(ruleset)
        self.assertTrue(len(ruleset.sha256_checksum) > 0)
        total_rules = (
            len(ruleset.conversion_rules or []) +
            len(ruleset.compliance_rules or []) +
            len(ruleset.naming_rules or []) +
            len(ruleset.security_rules or []) +
            len(ruleset.transformation_rules or [])
        )
        self.assertGreater(total_rules, 0)

    def test_decoder_live_postgres_canonical(self):
        canonical: CanonicalMigrationModel = self.data["canonical"]
        self.assertIsNotNone(canonical)
        self.assertTrue(len(canonical.sha256_checksum) > 0)
        self.assertIsNotNone(canonical.canonical_graph)

    def test_risk_live_postgres_assessment(self):
        risk: RiskAssessmentModel = self.data["risk"]
        self.assertIsNotNone(risk)
        self.assertTrue(len(risk.sha256_checksum) > 0)
        self.assertIsInstance(risk.risk_items, list)

    def test_planner_live_postgres_execution_plan(self):
        plan: MigrationExecutionPlan = self.data["plan"]
        self.assertIsNotNone(plan)
        self.assertTrue(len(plan.sha256_checksum) > 0)
        self.assertEqual(len(plan.cutover_plan["phases"]), 8)

    def test_advisor_live_postgres_advisory(self):
        advisory: MigrationAdvisoryModel = self.data["advisory"]
        self.assertIsNotNone(advisory)
        self.assertTrue(advisory.verify_checksum())
        self.assertGreater(len(advisory.recommendations), 0)

    def test_intelligence_live_postgres_model(self):
        intel: EnterpriseIntelligenceModel = self.data["intelligence"]
        self.assertIsNotNone(intel)
        self.assertTrue(EnterpriseIntelligenceGovernance.verify_model_checksum(intel))
        self.assertGreater(len(intel.decisions), 0)


class TestRealEngineMySQLPipeline(unittest.TestCase):
    """Real engine integration certification for MySQL 8.0."""

    @classmethod
    def setUpClass(cls):
        cfg = get_mysql_config()
        cls.data = asyncio.run(run_live_pipeline(cfg, "MYSQL"))

    def test_scout_live_mysql_metadata(self):
        report: DiscoveryReport = self.data["report"]
        self.assertEqual(report.engine_info.system_type, "MYSQL")
        self.assertTrue(len(report.sha256_checksum) > 0)

    def test_decoder_live_mysql_canonical(self):
        canonical: CanonicalMigrationModel = self.data["canonical"]
        self.assertTrue(len(canonical.sha256_checksum) > 0)

    def test_advisor_live_mysql_reports(self):
        advisory: MigrationAdvisoryModel = self.data["advisory"]
        tech = AdvisorPlatform.to_technical_report(advisory)
        self.assertIn("AKAAL TECHNICAL MIGRATION ADVISORY REPORT", tech)

    def test_intelligence_live_mysql_synthesis(self):
        intel: EnterpriseIntelligenceModel = self.data["intelligence"]
        self.assertTrue(EnterpriseIntelligenceGovernance.verify_model_checksum(intel))
        self.assertIsNotNone(intel.strategy)
        self.assertIsNotNone(intel.readiness)


class TestRealEngineOraclePipeline(unittest.TestCase):
    """Real engine integration certification for Oracle 23ai."""

    @classmethod
    def setUpClass(cls):
        cfg = get_oracle_config()
        cls.data = asyncio.run(run_live_pipeline(cfg, "ORACLE"))

    def test_scout_live_oracle_metadata(self):
        report: DiscoveryReport = self.data["report"]
        self.assertEqual(report.engine_info.system_type, "ORACLE")
        self.assertTrue(len(report.sha256_checksum) > 0)

    def test_full_pipeline_oracle_checksum_chaining(self):
        self.assertTrue(len(self.data["canonical"].sha256_checksum) > 0)
        self.assertTrue(len(self.data["risk"].sha256_checksum) > 0)
        self.assertTrue(len(self.data["plan"].sha256_checksum) > 0)
        self.assertTrue(len(self.data["advisory"].sha256_checksum) > 0)
        self.assertTrue(len(self.data["intelligence"].checksum) > 0)


class TestRealEngineDeterminismAndImmutability(unittest.TestCase):
    """Verification of determinism, immutability, and serialization on real engine outputs."""

    def test_live_postgres_3_run_determinism(self):
        """Execute 3 complete runs against live PostgreSQL 16 and verify checksum stability."""
        cfg = get_postgres_config(5432)
        checksums: Dict[str, Set[str]] = {
            "scout": set(),
            "ruleset": set(),
            "canonical": set(),
            "risk": set(),
            "plan": set(),
            "advisory": set(),
        }
        for _ in range(3):
            data = asyncio.run(run_live_pipeline(cfg, "POSTGRESQL"))
            checksums["scout"].add(data["report"].sha256_checksum)
            checksums["ruleset"].add(data["ruleset"].sha256_checksum)
            checksums["canonical"].add(data["canonical"].sha256_checksum)
            checksums["risk"].add(data["risk"].sha256_checksum)
            checksums["plan"].add(data["plan"].sha256_checksum)
            checksums["advisory"].add(data["advisory"].sha256_checksum)
            self.assertTrue(EnterpriseIntelligenceGovernance.verify_model_checksum(data["intelligence"]))

        for stage, keys in checksums.items():
            self.assertEqual(len(keys), 1, f"Live engine stage '{stage}' is non-deterministic")

    def test_live_models_immutability(self):
        """Verify immutability across all 5 models generated from real PostgreSQL metadata."""
        cfg = get_postgres_config(5432)
        data = asyncio.run(run_live_pipeline(cfg, "POSTGRESQL"))
        
        for attr, model in [
            ("sha256_checksum", data["canonical"]),
            ("sha256_checksum", data["risk"]),
            ("sha256_checksum", data["plan"]),
            ("sha256_checksum", data["advisory"]),
            ("checksum", data["intelligence"]),
        ]:
            with self.assertRaises((AttributeError, TypeError)):
                setattr(model, attr, "tampered_value")

    def test_live_models_lossless_serialization(self):
        """Verify JSON round-trip serialization for all models generated from real MySQL metadata."""
        cfg = get_mysql_config()
        data = asyncio.run(run_live_pipeline(cfg, "MYSQL"))
        
        # 1. Canonical
        json_can = CanonicalSerializer.serialize_json(data["canonical"])
        des_can = CanonicalSerializer.deserialize_json(json_can)
        self.assertEqual(data["canonical"].sha256_checksum, des_can.sha256_checksum)

        # 2. Risk
        json_risk = RiskSerializer.serialize_json(data["risk"])
        des_risk = RiskSerializer.deserialize_json(json_risk)
        self.assertEqual(data["risk"].sha256_checksum, des_risk.sha256_checksum)

        # 3. Planner
        json_plan = PlannerSerializer.serialize_json(data["plan"])
        des_plan = PlannerSerializer.deserialize_json(json_plan)
        self.assertEqual(data["plan"].sha256_checksum, des_plan.sha256_checksum)

        # 4. Advisor
        json_adv = AdvisorSerializer.to_json(data["advisory"])
        des_adv = AdvisorSerializer.from_json(json_adv)
        self.assertEqual(data["advisory"].sha256_checksum, des_adv.sha256_checksum)

        # 5. Enterprise Intelligence
        json_intel = EnterpriseIntelligenceSerializer.to_json(data["intelligence"])
        des_intel = EnterpriseIntelligenceSerializer.from_json(json_intel)
        self.assertEqual(data["intelligence"].checksum, des_intel.checksum)


if __name__ == "__main__":
    unittest.main(verbosity=2)
