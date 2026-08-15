"""
AKAAL Canonical CDC Causality Graph Engine (P3.7).
===================================================
Constructs, tracks, persists, and resolves transaction dependency graphs for out-of-order parallel replay.
Detects dependency cycles deterministically and enforces safe causal ordering.
"""

import threading
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from akaal.cdc.domain.events import CDCEventIdentity, CDCEvent, CDCTransaction
from akaal.cdc.domain.positions import CDCSourcePosition
from akaal.cdc.domain.errors import CDCExecutionError, CDCFailure, CDCFailureType, CDCFailureCategory
from akaal.cdc.ordering.domain import (
    CDCCausalIdentity,
    CDCDependencyEdge,
    CDCDependencyType,
    CDCTransactionDependencySet,
    CDCDependencyResolutionState,
    CDCCausalityGraph,
)
from akaal.core.state.state_store import CentralStateStore

logger = logging.getLogger(__name__)


class CDCCausalityGraphEngine:
    """Canonical Master Engine for Transactional Causality Graph Construction & Dependency Resolution."""

    def __init__(
        self,
        cdc_session_id: str,
        state_store: Optional[CentralStateStore] = None,
        fk_relationships: Optional[Dict[str, str]] = None,  # child_table -> parent_table
    ) -> None:
        self._lock = threading.RLock()
        self.cdc_session_id = cdc_session_id
        self.state_store = state_store or CentralStateStore()
        self.fk_relationships = fk_relationships or {}

        # Node map: tx_id -> tx_dict representation
        self.nodes: Dict[str, Dict[str, Any]] = {}
        # Entity index: f"{table}:{entity_key}" -> List of tx_ids in arrival order
        self.entity_history: Dict[str, List[str]] = {}
        # Predecessors map: tx_id -> Set of tx_ids that must complete before tx_id
        self.predecessors: Dict[str, Set[str]] = {}
        # Successors map: tx_id -> Set of tx_ids waiting for tx_id
        self.successors: Dict[str, Set[str]] = {}
        # Edge details map: f"{src}->{tgt}" -> CDCDependencyEdge
        self.edge_details: Dict[str, CDCDependencyEdge] = {}

        # Tracking status
        self.completed_txs: Set[str] = set()
        self.failed_txs: Set[str] = set()

        self._load_persistent_graph()

    def _get_graph_state_key(self) -> str:
        return f"cdc_causality_graph_{self.cdc_session_id}"

    def _persist_graph(self) -> None:
        if not self.state_store:
            return
        key = self._get_graph_state_key()
        edges_list = [e.to_dict() for e in self.edge_details.values()]
        payload = {
            "cdc_session_id": self.cdc_session_id,
            "nodes": self.nodes,
            "entity_history": self.entity_history,
            "predecessors": {k: list(v) for k, v in self.predecessors.items()},
            "successors": {k: list(v) for k, v in self.successors.items()},
            "completed_txs": list(self.completed_txs),
            "failed_txs": list(self.failed_txs),
            "edges": edges_list,
        }
        self.state_store.set_state(key, payload, category="causality_graph")

    def _load_persistent_graph(self) -> bool:
        if not self.state_store:
            return False
        with self._lock:
            key = self._get_graph_state_key()
            data = self.state_store.get_state(key, category="causality_graph")
            if data is not None:
                if not isinstance(data, dict) or data.get("cdc_session_id") != self.cdc_session_id:
                    fail = CDCFailure(
                        failure_type=CDCFailureType.CAUSAL_STATE_CORRUPTION,
                        category=CDCFailureCategory.BLOCKING,
                        message=f"[CAUSAL STATE CORRUPTION] Persisted graph for session '{self.cdc_session_id}' is corrupt or session-mismatched.",
                        migration_id="mig-unknown",
                        job_id="job-unknown",
                        run_id="run-unknown",
                        cdc_session_id=self.cdc_session_id,
                    )
                    raise CDCExecutionError(fail)
                try:
                    self.nodes = data.get("nodes", {})
                    self.entity_history = data.get("entity_history", {})
                    self.predecessors = {k: set(v) for k, v in data.get("predecessors", {}).items()}
                    self.successors = {k: set(v) for k, v in data.get("successors", {}).items()}
                    self.completed_txs = set(data.get("completed_txs", []))
                    self.failed_txs = set(data.get("failed_txs", []))
                    for e_dict in data.get("edges", []):
                        edge = CDCDependencyEdge.from_dict(e_dict)
                        edge_key = f"{edge.source_tx_id}->{edge.target_tx_id}"
                        self.edge_details[edge_key] = edge
                    logger.info(f"[CausalityGraph] Reconstructed {len(self.nodes)} nodes from CentralStateStore for session '{self.cdc_session_id}'")
                    return True
                except Exception as exc:
                    fail = CDCFailure(
                        failure_type=CDCFailureType.CAUSAL_STATE_CORRUPTION,
                        category=CDCFailureCategory.BLOCKING,
                        message=f"[CAUSAL STATE CORRUPTION] Failed to parse persisted graph state: {exc}",
                        migration_id="mig-unknown",
                        job_id="job-unknown",
                        run_id="run-unknown",
                        cdc_session_id=self.cdc_session_id,
                    )
                    raise CDCExecutionError(fail)
            return False

    def extract_entity_keys(self, transaction: CDCTransaction) -> Set[Tuple[str, str]]:
        """Extracts set of (table_name, entity_key) tuples touched by transaction events."""
        keys: Set[Tuple[str, str]] = set()
        for evt in transaction.events:
            table_name = evt.source_table
            image = evt.after_image or evt.before_image or {}

            # Primary key check
            entity_val = None
            for pk_col in ["id", "uuid", "pk", f"{table_name}_id", "_id"]:
                if pk_col in image:
                    entity_val = str(image[pk_col])
                    break
            if not entity_val and image:
                sorted_k = sorted(list(image.keys()))
                entity_val = f"{sorted_k[0]}:{image[sorted_k[0]]}"
            if not entity_val:
                entity_val = f"table-{table_name}"

            keys.add((table_name, entity_val))
        return keys

    def add_transaction(self, transaction: CDCTransaction) -> List[CDCDependencyEdge]:
        """
        Adds a transaction to the causality graph and automatically derives dependency edges.
        Detects same-entity, write-after-write, write-after-delete, and foreign key dependencies.
        Detects dependency cycles and fails closed.
        """
        with self._lock:
            tx_id = transaction.tx_id
            if tx_id in self.nodes:
                return [e for e in self.edge_details.values() if e.target_tx_id == tx_id]

            self.nodes[tx_id] = transaction.to_dict()
            if tx_id not in self.predecessors:
                self.predecessors[tx_id] = set()
            if tx_id not in self.successors:
                self.successors[tx_id] = set()

            entity_keys = self.extract_entity_keys(transaction)
            added_edges: List[CDCDependencyEdge] = []

            for table_name, entity_key in entity_keys:
                ent_hist_key = f"{table_name}:{entity_key}"
                history = self.entity_history.setdefault(ent_hist_key, [])

                # Add dependency on preceding active transactions for same entity
                curr_pos = transaction.commit_position
                for prev_tx_id in history:
                    if prev_tx_id != tx_id and prev_tx_id not in self.completed_txs:
                        prev_node = self.nodes.get(prev_tx_id)
                        prev_pos = None
                        if prev_node and "commit_position" in prev_node:
                            from akaal.cdc.domain.positions import parse_source_position
                            prev_pos = parse_source_position(prev_node["commit_position"])

                        if prev_pos and curr_pos and prev_pos > curr_pos:
                            src_id, tgt_id = tx_id, prev_tx_id
                        else:
                            src_id, tgt_id = prev_tx_id, tx_id

                        dep_type = CDCDependencyType.SAME_ENTITY
                        edge = CDCDependencyEdge(
                            source_tx_id=src_id,
                            target_tx_id=tgt_id,
                            dependency_type=dep_type,
                            description=f"Same entity '{ent_hist_key}' ordering ({src_id} -> {tgt_id})",
                            is_satisfied=(src_id in self.completed_txs),
                        )
                        self.add_dependency_edge(edge)
                        added_edges.append(edge)

                # Check Foreign Key relationships
                if table_name in self.fk_relationships:
                    parent_table = self.fk_relationships[table_name]
                    # Find parent transactions that inserted/modified parent table
                    parent_hist_prefix = f"{parent_table}:"
                    for hist_key, hist_txs in self.entity_history.items():
                        if hist_key.startswith(parent_hist_prefix):
                            for p_tx_id in hist_txs:
                                if p_tx_id != tx_id and p_tx_id not in self.completed_txs:
                                    edge = CDCDependencyEdge(
                                        source_tx_id=p_tx_id,
                                        target_tx_id=tx_id,
                                        dependency_type=CDCDependencyType.FOREIGN_KEY_PARENT_CHILD,
                                        description=f"FK Parent-Child dependency ({parent_table} -> {table_name})",
                                        is_satisfied=(p_tx_id in self.completed_txs),
                                    )
                                    self.add_dependency_edge(edge)
                                    added_edges.append(edge)

                history.append(tx_id)

            # Check dependency cycle
            if self.detect_cycle(tx_id):
                fail = CDCFailure(
                    failure_type=CDCFailureType.CAUSALITY_CYCLE_DETECTED,
                    category=CDCFailureCategory.BLOCKING,
                    message=f"[CAUSALITY CYCLE DETECTED] Dependency cycle detected for transaction '{tx_id}'.",
                    migration_id=transaction.identity.migration_id,
                    job_id=transaction.identity.job_id,
                    run_id=transaction.identity.run_id,
                    cdc_session_id=transaction.identity.cdc_session_id,
                )
                raise CDCExecutionError(fail)

            self._persist_graph()
            return added_edges

    def add_dependency_edge(self, edge: CDCDependencyEdge) -> None:
        """Adds an explicit dependency edge (source_tx_id -> target_tx_id)."""
        with self._lock:
            src = edge.source_tx_id
            tgt = edge.target_tx_id
            if src == tgt:
                fail = CDCFailure(
                    failure_type=CDCFailureType.INVALID_DEPENDENCY_EDGE,
                    category=CDCFailureCategory.BLOCKING,
                    message=f"[INVALID DEPENDENCY EDGE] Self-dependency edge '{src} -> {tgt}' rejected.",
                    migration_id="mig-unknown",
                    job_id="job-unknown",
                    run_id="run-unknown",
                    cdc_session_id=self.cdc_session_id,
                )
                raise CDCExecutionError(fail)

            edge_key = f"{src}->{tgt}"

            if src not in self.successors:
                self.successors[src] = set()
            self.successors[src].add(tgt)

            if tgt not in self.predecessors:
                self.predecessors[tgt] = set()
            self.predecessors[tgt].add(src)

            self.edge_details[edge_key] = edge

    def resolve_transaction_completion(self, tx_id: str) -> List[str]:
        """
        Marks transaction tx_id as COMPLETED.
        Satisfies outgoing edges and returns list of newly unblocked successor transaction IDs.
        """
        with self._lock:
            self.completed_txs.add(tx_id)
            unblocked: List[str] = []

            # Satisfy outgoing edges
            succs = self.successors.get(tx_id, set())
            for succ_id in succs:
                edge_key = f"{tx_id}->{succ_id}"
                if edge_key in self.edge_details:
                    self.edge_details[edge_key].is_satisfied = True

                # Check if successor is fully unblocked
                if self.is_transaction_ready(succ_id):
                    unblocked.append(succ_id)

            self._persist_graph()
            logger.info(f"[CausalityGraph] Resolved completion for tx='{tx_id}', unblocked {len(unblocked)} successors.")
            return unblocked

    def resolve_transaction_failure(self, tx_id: str) -> List[str]:
        """Marks transaction tx_id as FAILED. Successors become blocked by failed predecessor."""
        with self._lock:
            self.failed_txs.add(tx_id)
            affected = list(self.successors.get(tx_id, set()))
            self._persist_graph()
            logger.warning(f"[CausalityGraph] Transaction '{tx_id}' marked FAILED, blocking {len(affected)} successors.")
            return affected

    def is_transaction_ready(self, tx_id: str) -> bool:
        """Returns True if all predecessor transactions of tx_id are completed and satisfied."""
        with self._lock:
            if tx_id in self.failed_txs:
                return False
            if tx_id in self.completed_txs:
                return True
            preds = self.predecessors.get(tx_id, set())
            for p in preds:
                if p in self.failed_txs or p not in self.completed_txs:
                    return False
            return True

    def get_blocker_tx_ids(self, tx_id: str) -> List[str]:
        """Returns list of active predecessor transaction IDs blocking tx_id."""
        with self._lock:
            preds = self.predecessors.get(tx_id, set())
            return [p for p in preds if p not in self.completed_txs]

    def has_failed_predecessor(self, tx_id: str) -> bool:
        """Returns True if any predecessor of tx_id has failed."""
        with self._lock:
            preds = self.predecessors.get(tx_id, set())
            for p in preds:
                if p in self.failed_txs:
                    return True
            return False

    def detect_cycle(self, start_tx_id: str) -> bool:
        """Detects dependency cycles involving start_tx_id using Tarjan DFS traversal."""
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for succ in self.successors.get(node, set()):
                if succ not in visited:
                    if dfs(succ):
                        return True
                elif succ in rec_stack:
                    return True
            rec_stack.remove(node)
            return False

        return dfs(start_tx_id)

    def get_graph_summary(self) -> Dict[str, Any]:
        """Returns backend-authoritative graph telemetry summary."""
        with self._lock:
            ready_count = sum(1 for tx in self.nodes if self.is_transaction_ready(tx) and tx not in self.completed_txs)
            blocked_count = len(self.nodes) - len(self.completed_txs) - ready_count
            return {
                "cdc_session_id": self.cdc_session_id,
                "node_count": len(self.nodes),
                "edge_count": len(self.edge_details),
                "completed_count": len(self.completed_txs),
                "failed_count": len(self.failed_txs),
                "ready_count": ready_count,
                "blocked_count": max(blocked_count, 0),
            }
