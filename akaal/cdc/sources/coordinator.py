"""
AKAAL CDC Capture Orchestration Coordinator & Gateway Binding.
==============================================================
Orchestrates database miner instances, validates prerequisites, initializes capture streams,
and updates CentralStateStore monitoring without fabricating UI state.
"""

from typing import Dict, Any, Optional, List
import logging

from akaal.cdc.sources.base import ICDCSourceAdapter
from akaal.cdc.sources.postgres import PostgresWALMiner
from akaal.cdc.sources.mysql import MySQLBinlogMiner
from akaal.cdc.sources.oracle import OracleRedoMiner
from akaal.cdc.sources.sqlserver import MSSQLCDCMiner
from akaal.cdc.sources.mongodb import MongoDBOplogMiner

from akaal.cdc.domain.positions import CDCSourcePosition, parse_source_position, PostgresLSNPosition, MySQLGTIDPosition, OracleSCNPosition, MSSQLChangePosition, MongoDBOpLogPosition
from akaal.cdc.domain.events import CDCEventIdentity, CDCTransaction
from akaal.cdc.domain.consistency import CDCConsistencyBoundary
from akaal.cdc.domain.lifecycle import CDCSessionState, CDCSessionStateMachine
from akaal.cdc.domain.telemetry import CDCMonitoringDTO
from akaal.cdc.domain.errors import CDCFailure, CDCFailureCategory, CDCFailureType, CDCExecutionError
from akaal.core.state.state_store import CentralStateStore

logger = logging.getLogger(__name__)


class CDCCaptureCoordinator:
    """
    Central Controller for CDC Source Miners and Capture Pipeline.
    Binds CDC control requests (validate, initialize, start, poll, pause, stop) to EngineGateway.
    """

    MINER_REGISTRY = {
        "POSTGRESQL": PostgresWALMiner,
        "POSTGRES": PostgresWALMiner,
        "MYSQL": MySQLBinlogMiner,
        "ORACLE": OracleRedoMiner,
        "MSSQL": MSSQLCDCMiner,
        "MONGODB": MongoDBOplogMiner,
    }

    def __init__(self, state_store: Optional[CentralStateStore] = None) -> None:
        self.state_store = state_store or CentralStateStore.get_instance()
        self.active_miners: Dict[str, ICDCSourceAdapter] = {}
        self.session_state_machines: Dict[str, CDCSessionStateMachine] = {}
        self.consistency_boundaries: Dict[str, CDCConsistencyBoundary] = {}
        self.events_captured_count: Dict[str, int] = {}

    def get_miner_for_engine(self, engine: str) -> ICDCSourceAdapter:
        cls = self.MINER_REGISTRY.get(engine.upper())
        if not cls:
            raise ValueError(f"No CDC capture miner available for engine '{engine}'")
        return cls()

    def validate_cdc_prerequisites(self, engine: str, source_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validates engine-specific CDC prerequisites without creating active streaming state."""
        miner = self.get_miner_for_engine(engine)
        try:
            return miner.validate_prerequisites(source_config)
        finally:
            miner.close()

    def initialize_cdc_capture(
        self,
        engine: str,
        migration_id: str,
        job_id: str,
        run_id: str,
        cdc_session_id: str,
        initial_snapshot_position_dict: Dict[str, Any],
        source_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Validates prerequisites, initializes miner, and creates consistency boundary."""
        source_config = source_config or {}
        miner = self.get_miner_for_engine(engine)

        # Validate prerequisites
        miner.validate_prerequisites(source_config)

        # Parse position
        snapshot_pos = parse_source_position(initial_snapshot_position_dict)

        identity = CDCEventIdentity(
            migration_id=migration_id,
            job_id=job_id,
            run_id=run_id,
            cdc_session_id=cdc_session_id,
        )

        boundary = miner.initialize_capture(identity, snapshot_pos)
        sm = CDCSessionStateMachine(migration_id, job_id, run_id, cdc_session_id)
        sm.transition_to(CDCSessionState.INITIALIZING)

        self.active_miners[cdc_session_id] = miner
        self.session_state_machines[cdc_session_id] = sm
        self.consistency_boundaries[cdc_session_id] = boundary
        self.events_captured_count[cdc_session_id] = 0

        # Update monitoring
        self._publish_telemetry(cdc_session_id, "INITIALIZING")

        return {
            "cdc_session_id": cdc_session_id,
            "status": "INITIALIZING",
            "consistency_boundary": boundary.to_dict(),
            "capabilities": miner.capabilities.to_dict(),
        }

    def start_cdc_capture(self, cdc_session_id: str) -> Dict[str, Any]:
        """Transitions CDC session to CAPTURING state."""
        if cdc_session_id not in self.active_miners:
            raise ValueError(f"CDC session '{cdc_session_id}' is not initialized.")

        sm = self.session_state_machines[cdc_session_id]
        sm.transition_to(CDCSessionState.CAPTURING)
        self._publish_telemetry(cdc_session_id, "CAPTURING")

        return {
            "cdc_session_id": cdc_session_id,
            "status": "CAPTURING",
        }

    def poll_cdc_transactions(self, cdc_session_id: str) -> List[CDCTransaction]:
        """Polls active miner for committed CDCTransaction objects."""
        if cdc_session_id not in self.active_miners:
            raise ValueError(f"CDC session '{cdc_session_id}' is not active.")

        miner = self.active_miners[cdc_session_id]
        poll_func = getattr(miner, "poll_transactions", None)
        if not poll_func:
            return []

        committed_txs: List[CDCTransaction] = poll_func()
        total_evts = sum(len(tx.events) for tx in committed_txs)
        self.events_captured_count[cdc_session_id] = self.events_captured_count.get(cdc_session_id, 0) + total_evts

        if committed_txs:
            boundary = self.consistency_boundaries[cdc_session_id]
            boundary.update_captured_position(miner.get_current_position())
            self._publish_telemetry(cdc_session_id, "CAPTURING")

        return committed_txs

    def pause_cdc_capture(self, cdc_session_id: str) -> Dict[str, Any]:
        if cdc_session_id in self.session_state_machines:
            sm = self.session_state_machines[cdc_session_id]
            sm.transition_to(CDCSessionState.PAUSED)
            self._publish_telemetry(cdc_session_id, "PAUSED")
        return {"cdc_session_id": cdc_session_id, "status": "PAUSED"}

    def stop_cdc_capture(self, cdc_session_id: str) -> Dict[str, Any]:
        if cdc_session_id in self.active_miners:
            miner = self.active_miners.pop(cdc_session_id)
            miner.close()
        if cdc_session_id in self.session_state_machines:
            sm = self.session_state_machines[cdc_session_id]
            sm.transition_to(CDCSessionState.TERMINATED)
            self._publish_telemetry(cdc_session_id, "TERMINATED")
        return {"cdc_session_id": cdc_session_id, "status": "TERMINATED"}

    def _publish_telemetry(self, cdc_session_id: str, status: str) -> None:
        sm = self.session_state_machines.get(cdc_session_id)
        boundary = self.consistency_boundaries.get(cdc_session_id)
        miner = self.active_miners.get(cdc_session_id)

        dto = CDCMonitoringDTO(
            cdc_session_id=cdc_session_id,
            migration_id=sm.migration_id if sm else "unknown",
            job_id=sm.job_id if sm else "unknown",
            run_id=sm.run_id if sm else "unknown",
            status=status,
            capture_status=status,
            events_captured_total=self.events_captured_count.get(cdc_session_id, 0),
            captured_position=miner.get_current_position().to_string() if miner else None,
        )
        # Record in state store
        self.state_store.update_cdc_telemetry(cdc_session_id, dto.to_dict())
