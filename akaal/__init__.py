"""
Akaal — Enterprise Database Migration Platform
===============================================
End-to-end migration supporting 17 database/storage types and 9 cloud platforms.

Pipeline:
  Schema Analysis → Risk Scoring → Migration Planning → Advisory
      ↓
  Agent Fleet (Scout → GB → Validator → CDC → Checkpoint)
      ↓
  Human Approval Gate → Production Migration → Validation
"""

__version__ = "1.0.0"
__author__  = "Akaal"

from akaal.core.pipeline import AkaalPipeline, MigrationConfig
from akaal.core.logging_manager import configure_logging, migration_context
from akaal.scout.api.scout_platform import ScoutPlatform, discover
from akaal.rulebook.api.rulebook_platform import RulebookPlatform, generate_ruleset
from akaal.decoder.api.decoder_platform import DecoderPlatform, normalize
from akaal.risk.api.risk_platform import RiskPlatform, assess_risk
from akaal.planner.api.planner_platform import PlannerPlatform, build_execution_plan
