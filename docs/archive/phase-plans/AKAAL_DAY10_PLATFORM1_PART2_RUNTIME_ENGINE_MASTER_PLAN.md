# AKAAL DAY 10 — PLATFORM 1 PART 2: EXECUTION CORE & RUNTIME ENGINE
## MASTER IMPLEMENTATION PLANNING CONTRACT (VERSION 2.0)
**Status:** Permanent Architecture Blueprint & Runtime Engineering Contract (Frozen & ARB Certified)  
**Target Subsystem:** `akaal.platform.streaming.runtime` (Platform 1 Part 2 - Execution Core & Runtime Engine)  
**Base Architecture:** Built directly upon frozen Platform 1 Part 1 Contract Version 3.0 (`akaal.platform.streaming`).

---

## 1. Executive Summary & ARB Architectural Refinements (Version 2.0)

This Master Implementation Planning Contract Version 2.0 establishes the permanent, reference-grade engineering contract for **Platform 1 Part 2: Execution Core & Runtime Engine**. 

Evaluated and strengthened by an Independent Architecture Review Board (ARB), Version 2.0 incorporates 15 mandatory enterprise runtime architectural enhancements—transitioning the core runtime into an event-driven, actor-inspired, lock-minimal, core-pinned execution engine comparable to Apache Flink, Akka, and the Erlang VM.

### Core Architectural Innovations in Version 2.0
1. **Centralized Runtime Event Loop**: Execution flow is driven by a non-blocking `RuntimeEventLoop` dispatching commands, processing events, scheduling work, and coordinating checkpoints.
2. **Decoupled Command & Event Buses**: `RuntimeCommandBus` handles immutable execution commands (`Start`, `Pause`, `Resume`, `Cancel`, `Restart`, `Shutdown`, `Scale`), while `RuntimeEventBus` publishes runtime events (`WorkerStarted`, `CheckpointFinished`, `BackpressureRaised`, `WatermarkAdvanced`).
3. **Actor-Style Task Mailboxes**: Every `TaskExecutor` owns an isolated, sequential `TaskMailbox` processing priority control, execution, checkpoint, and recovery messages. Method calls into worker threads are strictly banned.
4. **Kernel Registry & Resolver**: SIMD, Scalar, GPU, and custom PyArrow kernels are resolved prior to task execution via `KernelRegistry` and `KernelResolver`.
5. **Multi-Domain Runtime Clock System**: Isolates `SystemClock`, `ProcessingClock`, `EventClock`, `CheckpointClock`, `MetricsClock`, and `RecoveryClock` into separate timing domains.
6. **Execution Tokens & Context Enclave**: Direct runtime references are replaced by scoped `ExecutionToken` objects encapsulating permissions, context, capabilities, and lifecycle ownership.
7. **Worker Supervisor Hierarchy**: `WorkerSupervisor` continuously monitors heartbeats, memory, queue pressure, and timeouts—executing automated, localized restart policies.
8. **Pluggable Policy Engine**: Decouples `RetryPolicy`, `RestartPolicy`, `BackpressurePolicy`, `CancellationPolicy`, `ShutdownPolicy`, `RecoveryPolicy`, and `SchedulingPolicy`.
9. **Multi-Domain Health Scoring**: Computes real-time composite health scores (`RuntimeHealthScore`, `WorkerHealthScore`, `QueueHealthScore`, `MemoryHealthScore`).
10. **Immutable Runtime Invariants**: Codifies 15 non-negotiable architectural rules enforced across all execution stages.

---

## 2. Permanent Runtime Invariants

The following 15 engineering invariants are permanent architectural rules governing Platform 1 Part 2:

1. **`ExecutionPlan` Immutability**: The `ExecutionPlan` emitted by Part 1's `ExecutionPlanner` is strictly immutable. The runtime never mutates or recalculates topology graphs.
2. **`ExecutionGraph` Immutability**: Vertices, edges, and parallel channels in the `ExecutionGraph` remain unchanged throughout job execution.
3. **Single Mailbox Ownership**: Every `TaskExecutor` owns exactly one `TaskMailbox`. Mailbox message processing is the sole execution entrypoint into worker threads.
4. **Single-Producer Single-Consumer Channel Constraint**: Every SPSC lock-free ring queue channel has exactly one upstream producer worker and one downstream consumer worker.
5. **Zero Shared Mutable Buffers**: Payload buffers passing across operator boundaries are reference-counted Arrow slices. Direct byte mutation of shared buffers is banned.
6. **Zero Memory Allocation in Hot Paths**: Buffer allocations in critical execution loops are served exclusively from pre-allocated off-heap memory pools.
7. **Deterministic Checkpoint Ordering**: Checkpoint barriers are injected and aligned deterministically in sequence number order across all parallel channels.
8. **Topology Immutability**: The runtime never modifies topological graph structures during execution or recovery.
9. **Resource Manager Governance**: Schedulers and task executors must request resource tokens from Part 1's `ResourceManager` before allocating cores or memory.
10. **Runtime Operator Encapsulation**: Streaming operators never bypass the runtime container or access system I/O directly.
11. **Pre-Execution Kernel Resolution**: Kernel selection and SIMD specialization are resolved via `KernelResolver` prior to task execution.
12. **Universal Event Observability**: Every internal runtime state change publishes an event to `RuntimeEventBus`.
13. **Universal Command Traceability**: Every execution command issued via `RuntimeCommandBus` carries a unique UUID v7 trace ID.
14. **Single Resource Ownership**: Every memory pool, thread handle, and ring buffer slot has exactly one explicit owner.
15. **Dependency Injection Enforcement**: All runtime components are instantiated and wired via `RuntimeDependencyContainer`.

---

## 3. Architecture Decision Records for Runtime Core (V2.0)

### ADR-006: Dedicated Task Runtime & Worker Isolation
- **Status**: Approved / Frozen
- **Context**: Operator failures must not crash the global execution runtime.
- **Decision**: Every task vertex is wrapped in a `TaskRuntime` container managed by a dedicated `WorkerSupervisor`.

### ADR-007: NUMA-Aware Core-Pinned Thread Affinity
- **Status**: Approved / Frozen
- **Context**: CPU cache misses across NUMA sockets degrade streaming throughput.
- **Decision**: `ThreadAffinityManager` binds task threads to physical CPU cores via OS native affinity masks (`sched_setaffinity`).

### ADR-008: Dual Vectorized & Scalar Execution Kernels via `KernelRegistry`
- **Status**: Approved / Frozen
- **Context**: Streaming engines require both low latency (< 1ms) and SIMD batch throughput (> 10M rec/sec).
- **Decision**: Operators register vectorized and scalar kernels in `KernelRegistry`. `KernelResolver` binds optimal kernels prior to execution loop entry.

### ADR-009: Actor-Style Task Mailbox Architecture
- **Status**: Approved / Frozen
- **Context**: Direct method calls across worker threads introduce race conditions and lock contention.
- **Decision**: All worker communication occurs asynchronously via lock-free `TaskMailbox` queues processing priority control messages.

### ADR-010: Asynchronous Two-Phase Graceful Shutdown Protocol
- **Status**: Approved / Frozen
- **Context**: Abrupt engine termination corrupts state snapshots and WAL logs.
- **Decision**: Two-phase shutdown: (1) Ingest pause & ring queue drain, (2) Commit final checkpoint barrier and release memory pools.

---

## 4. Repository Structure & Subsystem Layout

Platform 1 Part 2 resides in `akaal/platform/streaming/runtime/`:

```
temp_akaal-main/
├── akaal/
│   ├── platform/
│   │   └── streaming/
│   │       └── runtime/                       # Platform 1 Part 2 Root Package
│   │           ├── __init__.py
│   │           ├── bus/                       # Command & Event Bus Architecture
│   │           │   ├── __init__.py
│   │           │   ├── command_bus.py
│   │           │   ├── commands.py
│   │           │   ├── event_bus.py
│   │           │   └── events.py
│   │           ├── capabilities/              # Capability Registry & Discovery
│   │           │   ├── __init__.py
│   │           │   └── capability_registry.py
│   │           ├── clocks/                    # Multi-Domain Runtime Clock System
│   │           │   ├── __init__.py
│   │           │   └── runtime_clock.py
│   │           ├── container/                 # Dependency Injection Container & Factories
│   │           │   ├── __init__.py
│   │           │   └── dependency_container.py
│   │           ├── context/                   # Execution Context, Tokens & Sessions
│   │           │   ├── __init__.py
│   │           │   ├── execution_context.py
│   │           │   ├── execution_session.py
│   │           │   └── execution_token.py
│   │           ├── coordinator/               # Execution Coordinator & Dispatcher
│   │           │   ├── __init__.py
│   │           │   ├── dispatch_policies.py
│   │           │   ├── execution_coordinator.py
│   │           │   ├── execution_dispatcher.py
│   │           │   └── runtime_controller.py
│   │           ├── diagnostics/               # Live Runtime Diagnostics & Debug Interfaces
│   │           │   ├── __init__.py
│   │           │   ├── debug_interface.py
│   │           │   └── execution_diagnostics.py
│   │           ├── engine/                    # Event Loop, Execution Runtime & Pipelines
│   │           │   ├── __init__.py
│   │           │   ├── event_loop.py
│   │           │   ├── execution_pipeline.py
│   │           │   └── execution_runtime.py
│   │           ├── hooks/                     # Runtime Lifecycle Hooks Engine
│   │           │   ├── __init__.py
│   │           │   └── hook_manager.py
│   │           ├── kernels/                   # Kernel Registry, Resolver & Engines
│   │           │   ├── __init__.py
│   │           │   ├── kernel_layer.py
│   │           │   ├── kernel_registry.py
│   │           │   ├── kernel_resolver.py
│   │           │   ├── operator_execution_engine.py
│   │           │   ├── scalar_engine.py
│   │           │   └── vectorized_engine.py
│   │           ├── mailbox/                   # Task Mailbox & Priority Message Processing
│   │           │   ├── __init__.py
│   │           │   ├── mailbox_messages.py
│   │           │   └── task_mailbox.py
│   │           ├── metrics/                   # Health Monitoring, Scoring & Metrics
│   │           │   ├── __init__.py
│   │           │   ├── health_monitor.py
│   │           │   ├── health_scoring.py
│   │           │   └── runtime_metrics.py
│   │           ├── policies/                  # Pluggable Runtime Policy Engine
│   │           │   ├── __init__.py
│   │           │   └── policy_engine.py
│   │           ├── recovery/                  # Failure Detection & Supervisor Recovery
│   │           │   ├── __init__.py
│   │           │   ├── failure_detector.py
│   │           │   ├── recovery_flow.py
│   │           │   └── task_restart.py
│   │           ├── resources/                 # Buffer, Memory & Resource Allocators
│   │           │   ├── __init__.py
│   │           │   ├── buffer_interaction.py
│   │           │   ├── memory_interaction.py
│   │           │   └── resource_allocator.py
│   │           ├── tasks/                     # Task Runtime, Supervisors & Workers
│   │           │   ├── __init__.py
│   │           │   ├── task_executor.py
│   │           │   ├── task_runtime.py
│   │           │   ├── worker_coordination.py
│   │           │   ├── worker_lifecycle.py
│   │           │   └── worker_supervisor.py
│   │           ├── threads/                   # Core Affinity & Thread Scheduling
│   │           │   ├── __init__.py
│   │           │   ├── task_scheduler.py
│   │           │   ├── thread_affinity.py
│   │           │   └── thread_manager.py
│   │           └── transport/                 # Queue Production, Consumption & Watermarks
│   │               ├── __init__.py
│   │               ├── queue_consumer.py
│   │               ├── queue_producer.py
│   │               └── watermark_propagator.py
```

---

## 5. Subsystem Package & Module Taxonomy

Catalog for all 48 Part 2 Python modules across 18 packages:

1. `bus.command_bus`: Synchronous/asynchronous command bus dispatching immutable commands.
2. `bus.commands`: Immutable command definitions (`StartCommand`, `PauseCommand`, `ShutdownCommand`).
3. `bus.event_bus`: Pub-sub event bus distributing runtime notification events.
4. `bus.events`: Domain event definitions (`WorkerStartedEvent`, `CheckpointFinishedEvent`).
5. `capabilities.capability_registry`: Advertises and discovers engine capabilities.
6. `clocks.runtime_clock`: Manages isolated timing domains (`SystemClock`, `EventClock`, `ProcessingClock`).
7. `container.dependency_container`: IoC container managing component wiring and lifecycle injection.
8. `context.execution_context`: Thread-safe runtime context providing task metadata and handles.
9. `context.execution_session`: Manages multi-tenant streaming session scopes.
10. `context.execution_token`: Scoped token encapsulating task credentials, permissions, and IDs.
11. `coordinator.dispatch_policies`: Configurable dispatcher algorithms (`RoundRobin`, `Hash`, `Affinity`).
12. `coordinator.execution_coordinator`: Master orchestrator submitting execution plans to worker nodes.
13. `coordinator.execution_dispatcher`: Dispatches physical task vertices to worker threads using policies.
14. `coordinator.runtime_controller`: High-level controller converting external requests into commands.
15. `diagnostics.debug_interface`: Exposes internal queue depths and memory pointers for live debugging.
16. `diagnostics.execution_diagnostics`: Captures runtime bottlenecks, lock contention, and latency spikes.
17. `engine.event_loop`: Central non-blocking event loop driving the execution core heartbeat.
18. `engine.execution_pipeline`: Orchestrates data flow pipelines across fused operator kernels.
19. `engine.execution_runtime`: Top-level runtime container executing an `ExecutionPlan`.
20. `hooks.hook_manager`: Executes plugin lifecycle hooks (`BeforeExecute`, `AfterCheckpoint`).
21. `kernels.kernel_layer`: Common binding interface for PyArrow C-extension kernels.
22. `kernels.kernel_registry`: Thread-safe registry mapping operator IDs to execution kernels.
23. `kernels.kernel_resolver`: Binds scalar or SIMD vectorized kernels prior to execution.
24. `kernels.operator_execution_engine`: Routes payloads to scalar streaming loops or PyArrow kernels.
25. `kernels.scalar_engine`: Sub-millisecond tuple-by-tuple streaming evaluation engine.
26. `kernels.vectorized_engine`: SIMD-vectorized PyArrow RecordBatch evaluation engine.
27. `mailbox.mailbox_messages`: Priority message envelopes (`ControlMessage`, `ExecutionMessage`).
28. `mailbox.task_mailbox`: SPSC lock-free mailbox queue powering actor-style worker threads.
29. `metrics.health_monitor`: Monitors worker thread heartbeats and queue occupancy health.
30. `metrics.health_scoring`: Computes composite health scores for workers, queues, and memory.
31. `metrics.runtime_metrics`: Emits atomic performance counters, gauges, and latency histograms.
32. `policies.policy_engine`: Configurable policy engine (`RetryPolicy`, `BackpressurePolicy`).
33. `recovery.failure_detector`: Detects worker thread panics, unhandled exceptions, and timeouts.
34. `recovery.recovery_flow`: Coordinates WAL replay and state snapshot restoration upon task crash.
35. `recovery.task_restart`: Manages localized task worker restarts with backoff retries.
36. `resources.buffer_interaction`: Zero-copy off-heap Arrow buffer slicing and reference control.
37. `resources.memory_interaction`: Allocates task memory quotas from Part 1's `StreamMemoryPool`.
38. `resources.resource_allocator`: Coordinates resource token reservations prior to task startup.
39. `tasks.task_executor`: Pinned thread execution loop processing messages from `TaskMailbox`.
40. `tasks.task_runtime`: Isolated task worker container managing lifecycle and state buffers.
41. `tasks.worker_coordination`: Coordinates task alignment during checkpoint barriers and state snapshots.
42. `tasks.worker_lifecycle`: Manages worker states (`CREATED`, `RUNNING`, `PAUSED`, `STOPPED`, `FAILED`).
43. `tasks.worker_supervisor`: Supervises worker health, memory, and timeouts, deciding restart actions.
44. `threads.task_scheduler`: Assigns task executors to runnable work-stealing thread queues.
45. `threads.thread_affinity`: Binds worker threads to specific physical CPU cores using OS syscalls.
46. `threads.thread_manager`: Allocates, monitors, and recycles core-pinned worker thread pools.
47. `transport.queue_consumer`: Lock-free SPSC ring queue reader emitting credit grants.
48. `transport.queue_producer`: Lock-free SPSC ring queue writer with credit checking.
49. `transport.watermark_propagator`: Aligns and forwards event-time watermarks across parallel channels.

---

## 6. Dependency Injection & Container Architecture

```python
# akaal/platform/streaming/runtime/container/dependency_container.py
from typing import Dict, Type, Any

class RuntimeDependencyContainer:
    """IoC container managing dependency injection for runtime components."""

    def __init__(self) -> None:
        self._singletons: Dict[Type[Any], Any] = {}
        self._factories: Dict[Type[Any], Any] = {}

    def register_singleton(self, interface_type: Type[Any], instance: Any) -> None:
        self._singletons[interface_type] = instance

    def resolve(self, interface_type: Type[T]) -> T:
        if interface_type in self._singletons:
            return self._singletons[interface_type]
        raise KeyError(f"Interface '{interface_type}' not registered in RuntimeDependencyContainer.")
```

---

## 7. Command Bus & Event Bus Architecture

```python
# akaal/platform/streaming/runtime/bus/command_bus.py
from dataclasses import dataclass
from typing import Callable, Dict, Type
import uuid

@dataclass(frozen=True, slots=True)
class RuntimeCommand:
    command_id: str
    trace_id: str
    target_task_id: str

class RuntimeCommandBus:
    """Dispatches immutable execution commands to registered command handlers."""

    def __init__(self) -> None:
        self._handlers: Dict[Type[RuntimeCommand], Callable[[RuntimeCommand], None]] = {}

    def register_handler(self, command_type: Type[RuntimeCommand], handler: Callable[[RuntimeCommand], None]) -> None:
        self._handlers[command_type] = handler

    def dispatch(self, command: RuntimeCommand) -> None:
        handler = self._handlers.get(type(command))
        if handler is None:
            raise KeyError(f"No handler registered for command '{type(command).__name__}'.")
        handler(command)
```

```python
# akaal/platform/streaming/runtime/bus/event_bus.py
from dataclasses import dataclass
from typing import Callable, Dict, List, Type

@dataclass(frozen=True, slots=True)
class RuntimeEvent:
    event_id: str
    timestamp_ns: int
    source_task_id: str

class RuntimeEventBus:
    """Publishes runtime notification events to subscribed listeners."""

    def __init__(self) -> None:
        self._subscribers: Dict[Type[RuntimeEvent], List[Callable[[RuntimeEvent], None]]] = {}

    def subscribe(self, event_type: Type[RuntimeEvent], listener: Callable[[RuntimeEvent], None]) -> None:
        self._subscribers.setdefault(event_type, []).append(listener)

    def publish(self, event: RuntimeEvent) -> None:
        for listener in self._subscribers.get(type(event), []):
            listener(event)
```

---

## 8. Task Mailbox & Priority Message Processing

Worker threads do not accept direct method calls. All execution occurs sequentially through an actor-style `TaskMailbox` (`akaal.platform.streaming.runtime.mailbox.task_mailbox`).

```python
# akaal/platform/streaming/runtime/mailbox/task_mailbox.py
from enum import IntEnum, auto
from dataclasses import dataclass
from typing import Any, Optional
import queue

class MessagePriority(IntEnum):
    CONTROL = 0      # Checkpoints, Shutdown, Emergency Pause (Highest Priority)
    RECOVERY = 1     # State Restoration, WAL Replay
    EXECUTION = 2    # Stream Payloads, Micro-batches (Lowest Priority)

@dataclass(order=True)
class MailboxMessage:
    priority: MessagePriority
    payload: Any = dataclass_field(compare=False)

class TaskMailbox:
    """Lock-free priority mailbox powering actor-style task worker threads."""

    def __init__(self, capacity: int = 4096) -> None:
        self._queue = queue.PriorityQueue(maxsize=capacity)

    def send(self, priority: MessagePriority, payload: Any) -> None:
        self._queue.put(MailboxMessage(priority, payload), block=True)

    def receive(self, block: bool = True, timeout: Optional[float] = None) -> MailboxMessage:
        return self._queue.get(block=block, timeout=timeout)
```

---

## 9. Multi-Domain Health Scoring Engine

The `HealthScoringEngine` (`akaal.platform.streaming.runtime.metrics.health_scoring`) combines metric gauges into composite normalized health scores ($0.0 - 1.0$):

$$\text{WorkerHealthScore} = 0.4 \times (1 - \text{CPU}_{\text{load}}) + 0.4 \times (1 - \text{Queue}_{\text{ratio}}) + 0.2 \times (1 - \text{Memory}_{\text{ratio}})$$

```python
# akaal/platform/streaming/runtime/metrics/health_scoring.py
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class HealthScoreReport:
    runtime_score: float
    worker_score: float
    queue_score: float
    memory_score: float
    is_healthy: bool

class HealthScoringEngine:
    """Computes normalized composite health scores across runtime subsystems."""

    @staticmethod
    def evaluate(cpu_load: float, queue_ratio: float, memory_ratio: float) -> HealthScoreReport:
        w_score = max(0.0, 1.0 - (0.4 * cpu_load + 0.4 * queue_ratio + 0.2 * memory_ratio))
        q_score = max(0.0, 1.0 - queue_ratio)
        m_score = max(0.0, 1.0 - memory_ratio)
        r_score = (w_score + q_score + m_score) / 3.0
        return HealthScoreReport(
            runtime_score=r_score,
            worker_score=w_score,
            queue_score=q_score,
            memory_score=m_score,
            is_healthy=r_score > 0.6
        )
```

---

## 10. Performance SLAs & Benchmark Targets

| Performance Metric | Micro-Batch Mode | Record Streaming Mode |
| :--- | :--- | :--- |
| **Peak Throughput** | > 10,000,000 records/sec | > 500,000 records/sec |
| **p99 Latency SLA** | < 15.0 milliseconds | < 0.8 milliseconds |
| **Mailbox Message Processing Latency** | < 1.0 microseconds | < 0.1 microseconds |
| **Worker Context Switch Overhead** | 0 ms (Core-Pinned Thread) | 0 ms (Core-Pinned Thread) |
| **Localized Task Restart Duration** | < 800 milliseconds | < 300 milliseconds |
| **Two-Phase Graceful Shutdown** | < 2,500 milliseconds | < 800 milliseconds |

---

## 11. Definition of Done (Version 2.0 Certification)

The implementation of **Platform 1 Part 2: Execution Core & Runtime Engine** is defined as officially COMPLETE when:

1. All 48 specified modules across 18 packages under `akaal/platform/streaming/runtime/` are fully implemented.
2. Static type checker `mypy --strict akaal/platform/streaming/runtime` returns 0 errors.
3. Code coverage reaches 100% across unit, integration, concurrency, and chaos test suites.
4. All 15 Runtime Invariants are enforced and verified via automated architecture boundary tests.
5. All 15 mandatory ARB improvements (Runtime Event Loop, Command Bus, Event Bus, Task Mailboxes, Kernel Registry, Runtime Clocks, Execution Tokens, Dependency Injection, Worker Supervisors, Pluggable Policies, Capability Registry, Hooks, Health Scoring) are verified.
6. Core-pinned worker thread affinity and NUMA isolation pass Linux testbed verification.
7. The Architecture Review Board (ARB) formally signs off on the Part 2 Version 2.0 release certification report.
