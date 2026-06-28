from __future__ import annotations
import copy
import time
from typing import Any, Dict, List

from akaal.advisory.rulebook.resolver import SemanticResolver
from akaal.advisory.validator import validate, ValidationError
from akaal.advisory.planner.planner import plan_migration
from akaal.advisory.advisor.advisor import generate_advisory
from akaal.advisory.executor import execute as execute_migration


class OrchestratorV1:
    """
    V1 Deterministic Migration Orchestrator
    """

    def __init__(self):
        self._resolver = SemanticResolver()

    # -----------------------------
    # PUBLIC ENTRYPOINT
    # -----------------------------
    def run(self, migration_input: Dict[str, Any]) -> Dict[str, Any]:
        pipeline_log: List[str] = []
        start_time = time.monotonic()

        result: Dict[str, Any] = {
            "udm": None,
            "risk": None,
            "plan": None,
            "advisory": None,
            "execution": None,
            "final_status": "FAILED",
            "failed_stage": None,
            "error": None,
            "pipeline_log": pipeline_log,
        }

        source_type = migration_input.get("source_type")

        # -------------------------
        # PARSE
        # -------------------------
        pipeline_log.append("stage:parse:start")

        parser = self._get_parser(source_type)
        if parser is None:
            result["failed_stage"] = "parse"
            result["error"] = f"no_parser_for_engine:{source_type}"
            return self._finalize(result, start_time, pipeline_log)

        try:
            parsed = parser.parse(migration_input["raw_type"])
            pipeline_log.append("stage:parse:success")
        except Exception as exc:
            result["failed_stage"] = "parse"
            result["error"] = str(exc)
            return self._finalize(result, start_time, pipeline_log)

        # -------------------------
        # RESOLVE
        # -------------------------
        pipeline_log.append("stage:resolve:start")
        try:
            udm = self._resolver.resolve(parsed)
            pipeline_log.append("stage:resolve:success")
        except Exception as exc:
            result["failed_stage"] = "resolve"
            result["error"] = str(exc)
            return self._finalize(result, start_time, pipeline_log)

        result["udm"] = copy.deepcopy(udm)

        # -------------------------
        # RISK
        # -------------------------
        pipeline_log.append("stage:risk_scorer:start")
        try:
            risk = self._score_risk(udm)
            pipeline_log.append("stage:risk_scorer:success")
        except Exception as exc:
            result["failed_stage"] = "risk_scorer"
            result["error"] = str(exc)
            return self._finalize(result, start_time, pipeline_log)

        result["risk"] = copy.deepcopy(risk)

        # -------------------------
        # VALIDATE
        # -------------------------
        pipeline_log.append("stage:validator:start")
        try:
            validation = validate(udm)
            pipeline_log.append("stage:validator:success")
        except ValidationError as exc:
            result["failed_stage"] = "validator"
            result["error"] = ";".join(exc.errors)
            return self._finalize(result, start_time, pipeline_log)
        except Exception as exc:
            result["failed_stage"] = "validator"
            result["error"] = str(exc)
            return self._finalize(result, start_time, pipeline_log)

        udm = validation["udm"]

        # -------------------------
        # PLAN
        # -------------------------
        pipeline_log.append("stage:planner:start")
        try:
            plan = plan_migration(udm, risk)
            decision = str(plan.get("decision", "")).upper()
            pipeline_log.append(f"stage:planner:success:decision:{decision}")
        except Exception as exc:
            result["failed_stage"] = "planner"
            result["error"] = str(exc)
            return self._finalize(result, start_time, pipeline_log)

        result["plan"] = copy.deepcopy(plan)

        # -------------------------
        # ADVISOR (always runs)
        # -------------------------
        pipeline_log.append("stage:advisor:start")
        try:
            advisory = generate_advisory(udm, risk, plan)
            pipeline_log.append("stage:advisor:success")
        except Exception as exc:
            result["failed_stage"] = "advisor"
            result["error"] = str(exc)
            return self._finalize(result, start_time, pipeline_log)

        result["advisory"] = copy.deepcopy(advisory)

        # -------------------------
        # EXECUTOR
        # -------------------------
        if "BLOCK" in decision:
            pipeline_log.append("stage:executor:skipped:decision_is_BLOCK")
            result["final_status"] = "BLOCKED"
            return self._finalize(result, start_time, pipeline_log)

        pipeline_log.append("stage:executor:start")

        try:
            execution = execute_migration(udm, plan, source_engine=source_type)
            pipeline_log.append("stage:executor:success")
        except Exception as exc:
            result["failed_stage"] = "executor"
            result["error"] = str(exc)
            return self._finalize(result, start_time, pipeline_log)

        result["execution"] = copy.deepcopy(execution)
        result["final_status"] = "SUCCESS"

        return self._finalize(result, start_time, pipeline_log)

    # -----------------------------
    # INTERNAL HELPERS
    # -----------------------------
    def _get_parser(self, engine: str):
        from akaal.advisory.parsers.oracle import OracleParser
        from akaal.advisory.parsers.mysql import MySQLParser
        from akaal.advisory.parsers.postgresql import PostgreSQLParser

        registry = {
            "oracle": OracleParser(),
            "mysql": MySQLParser(),
            "postgresql": PostgreSQLParser(),
            "postgres": PostgreSQLParser(),
        }

        if not engine:
            return None
        return registry.get(engine.strip().lower())

    def _score_risk(self, udm: Dict[str, Any]) -> Dict[str, Any]:
        from akaal.advisory.risk_scorer.risk_scorer import RiskScorerV1
        return RiskScorerV1().score(udm)

    def _finalize(self, result, start_time, log):
        elapsed = int((time.monotonic() - start_time) * 1000)
        log.append(f"pipeline:complete:elapsed_ms:{elapsed}")
        return result