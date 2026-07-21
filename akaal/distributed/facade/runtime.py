"""
DistributedRuntimeV1 Public Façade module for Platform 2.
Single stable public entry point for external platforms to interact with the Distributed Runtime.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Tuple
from threading import RLock
import logging

from akaal.distributed.domain.identifiers import (
    ClusterId,
    NodeId,
    WorkerId,
    TaskId,
    ExecutionId,
    IdempotencyKey,
)
from akaal.distributed.domain.models import (
    Task,
    Worker,
    Node,
    ExecutionRequest,
    ExecutionResult,
    ResourceReservation,
)
from akaal.distributed.clock.clock import Clock, SystemClock
from akaal.distributed.repository.memory_repository import (
    InMemoryWorkerRepository,
    InMemoryClusterRepository,
    InMemoryTaskRepository,
    InMemoryLeaseRepository,
    InMemoryMembershipRepository,
)
from akaal.distributed.repository.state_store import ClusterStateStore
from akaal.distributed.events.events import InProcessEventDispatcher
from akaal.distributed.coordination.coordinator import CoordinatorService
from akaal.distributed.queue.queue import MemoryTaskQueue
from akaal.distributed.cluster.membership import ClusterMembershipService
from akaal.distributed.cluster.leader import LeadershipService
from akaal.distributed.cluster.health import ClusterHealthService
from akaal.distributed.worker.registry import WorkerRegistry
from akaal.distributed.worker.discovery import DiscoveryService
from akaal.distributed.worker.heartbeat import HeartbeatManager
from akaal.distributed.worker.lease import LeaseManager
from akaal.distributed.scheduler.selector import WorkerSelector
from akaal.distributed.scheduler.scheduler import ClusterScheduler
from akaal.distributed.resource.manager import ResourceManager
from akaal.distributed.resource.scaling import WorkerScalingManager
from akaal.distributed.execution.lifecycle import ExecutionLifecycleManager
from akaal.distributed.execution.recovery import RecoveryManager
from akaal.distributed.engine.distributed_engine import DefaultDistributedExecutionEngineV1
from akaal.distributed.metrics.metrics import InMemoryDistributedMetricsCollector
from akaal.distributed.config.config import DistributedRuntimeConfiguration

logger = logging.getLogger("nexusforge.distributed.runtime")


class DistributedRuntimeV1(ABC):
    """Abstract DistributedRuntimeV1 public facade contract."""

    @abstractmethod
    def submit_task(self, task: Task, idempotency_key: Optional[IdempotencyKey] = None) -> ExecutionRequest:
        pass

    @abstractmethod
    def register_worker(self, node_id: NodeId, capacity: int = 10) -> Worker:
        pass

    @abstractmethod
    def scale_up(self, node_id: NodeId, count: int = 1) -> List[Worker]:
        pass

    @abstractmethod
    def drain_worker(self, worker_id: WorkerId) -> Worker:
        pass

    @abstractmethod
    def get_cluster_health(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def process_next(self) -> Optional[ExecutionResult]:
        pass


class DefaultDistributedRuntimeV1(DistributedRuntimeV1):
    """
    Default production implementation of DistributedRuntimeV1.
    Assembles and encapsulates all Platform 2 internal runtime services.
    """

    def __init__(
        self,
        cluster_id: Optional[ClusterId] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        self._lock = RLock()
        self.clock = clock or SystemClock()
        self.cluster_id = cluster_id or ClusterId.generate()

        # Repositories
        self.worker_repo = InMemoryWorkerRepository()
        self.cluster_repo = InMemoryClusterRepository()
        self.task_repo = InMemoryTaskRepository()
        self.lease_repo = InMemoryLeaseRepository()
        self.membership_repo = InMemoryMembershipRepository()

        # Event Dispatcher & Metrics
        self.dispatcher = InProcessEventDispatcher()
        self.metrics = InMemoryDistributedMetricsCollector()

        # State Store & Coordinator
        self.state_store = ClusterStateStore(self.cluster_repo, self.worker_repo, self.membership_repo)
        self.coordinator = CoordinatorService(self.dispatcher)

        # Services
        self.membership_service = ClusterMembershipService(self.membership_repo, self.dispatcher)
        self.leadership_service = LeadershipService(self.membership_service, self.dispatcher, clock=self.clock)
        self.health_service = ClusterHealthService(
            self.membership_service, self.leadership_service, self.worker_repo, self.lease_repo, clock=self.clock
        )

        self.registry = WorkerRegistry(self.worker_repo, self.dispatcher, clock=self.clock)
        self.discovery = DiscoveryService(self.worker_repo)
        self.heartbeat_manager = HeartbeatManager(self.worker_repo, self.dispatcher, clock=self.clock)
        self.lease_manager = LeaseManager(self.lease_repo, self.dispatcher, clock=self.clock)

        self.worker_selector = WorkerSelector(self.discovery)
        self.scheduler = ClusterScheduler(self.worker_selector, self.dispatcher, clock=self.clock)

        self.resource_manager = ResourceManager(clock=self.clock)
        self.scaling_manager = WorkerScalingManager(self.registry, self.dispatcher)

        self.queue = MemoryTaskQueue(clock=self.clock)
        self.lifecycle_manager = ExecutionLifecycleManager(self.dispatcher, clock=self.clock)
        self.recovery_manager = RecoveryManager(
            self.task_repo, self.lease_repo, self.worker_repo, self.state_store, self.dispatcher, clock=self.clock
        )

        # Execution Engine
        self.engine = DefaultDistributedExecutionEngineV1(
            queue=self.queue,
            scheduler=self.scheduler,
            lease_manager=self.lease_manager,
            registry=self.registry,
            lifecycle_manager=self.lifecycle_manager,
            recovery_manager=self.recovery_manager,
            dispatcher=self.dispatcher,
            clock=self.clock,
            metrics=self.metrics,
        )

        # Initial node join and leader election
        primary_node = Node(node_id=NodeId("node_primary"), hostname="localhost", ip_address="127.0.0.1")
        self.membership_service.join_node(self.cluster_id, primary_node)
        self.leadership_service.run_election(self.cluster_id, primary_node.node_id)

    def submit_task(self, task: Task, idempotency_key: Optional[IdempotencyKey] = None) -> ExecutionRequest:
        return self.engine.submit_execution(task, idempotency_key=idempotency_key)

    def register_worker(self, node_id: NodeId, capacity: int = 10) -> Worker:
        return self.registry.register_worker(node_id=node_id, capacity=capacity)

    def scale_up(self, node_id: NodeId, count: int = 1) -> List[Worker]:
        return self.scaling_manager.scale_up(node_id, count=count)

    def drain_worker(self, worker_id: WorkerId) -> Worker:
        return self.scaling_manager.drain_worker(worker_id)

    def get_cluster_health(self) -> Dict[str, Any]:
        return self.health_service.get_cluster_health(self.cluster_id)

    def process_next(self) -> Optional[ExecutionResult]:
        return self.engine.process_next_task()
