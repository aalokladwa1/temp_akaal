# AKAAL DAY 10 — PLATFORM 1 PART 1: GENERIC STREAMING EXECUTION ENGINE
## MASTER IMPLEMENTATION PLANNING CONTRACT (VERSION 3.0)
**Status:** Permanent Architecture Blueprint & Enterprise Engineering Contract (Frozen & ARB Certified)  
**Target Subsystem:** `akaal.platform.streaming` (Platform 1 - Generic Streaming Execution Engine)  
**Strict Domain Boundary:** Zero Knowledge of Databases, Migrations, Workflows, or Business Logic. Generic Stream Processing Only.

---

## 1. Executive Summary & ARB Architectural Refinements (V3.0)

This Master Implementation Planning Contract Version 3.0 represents the definitive, enterprise-grade engineering contract for **Platform 1 Part 1: Generic Streaming Execution Engine** within the AKAAL platform ecosystem. Evaluated and refined by an Independent Architecture Review Board (ARB), Version 3.0 incorporates 15 mandatory enterprise architectural enhancements and establishes permanent design decisions before implementation begins.

Platform 1 is engineered strictly as a high-throughput, low-latency, generic stream processing engine capable of hybrid execution (record-by-record streaming and Apache Arrow micro-batching) with zero-copy buffer management, event-time windowing, adaptive stream joining, deterministic operator graph compilation, state backend abstraction, and end-to-end backpressure propagation.

### Core Architectural Axioms
1. **Generic Abstraction**: The execution engine contains zero knowledge of databases, schema migrations, business workflows, domain rules, or application-specific payloads. It operates exclusively on generic streaming primitives: raw memory buffers, Apache Arrow record batches, event timestamps, watermarks, sequence numbers, and typed partition keys.
2. **Stream Graph Pipeline Architecture**: Clear 4-tier separation: `LogicalStreamGraph` $\rightarrow$ `OptimizedStreamGraph` $\rightarrow$ `PhysicalStreamGraph` $\rightarrow$ `ExecutionGraph`, driven by a cost-based/rule-based `GraphOptimizer` and compiled via an `OperatorCompiler`.
3. **ExecutionPlanner Decoupling**: The runtime does not construct execution topologies. `ExecutionPlanner` lowers the physical graph into an immutable `ExecutionPlan`, which `ExecutionRuntime` executes deterministically.
4. **State Backend Abstraction**: State persistence is completely decoupled via `IStateBackend` supporting `InMemoryStateBackend`, `RocksDBStateBackend`, `RedisStateBackend`, and custom durable stores.
5. **Unified Serialization Registry**: Single entrypoint `SerializationRegistry` managing Apache Arrow IPC, JSON, Protobuf, and binary codecs zero-copy.
6. **Centralized Operator Lifecycle Governance**: Every operator state transition (`CREATED`, `INITIALIZED`, `OPEN`, `RUNNING`, `CHECKPOINTING`, `RESTORING`, `STOPPING`, `STOPPED`, `FAILED`, `DESTROYED`) is managed by `OperatorLifecycleManager`.
7. **Comprehensive System Diagnostics & Profiling**: Embedded `MemoryDiagnostics` (leak detection, fragmentation tracking, buffer lifetime analyzer) and `BufferDiagnostics` (copy detector, spill analyzer, allocation heatmaps).
8. **Adaptive Resource Manager & Dynamic Scheduler**: Central `ResourceManager` controlling CPU, Memory, Buffers, Queues, and Tokens coupled with an `AdaptiveScheduler` modifying execution parameters based on real-time backpressure, queue depths, watermarks, and CPU load.
9. **Live Inspection & Automated Performance Advisor**: Real-time `RuntimeInspector` exposing live topology state and `PerformanceAdvisor` continuously emitting optimization recommendations.

---

## 2. Architecture Decision Records (ADRs)

### ADR-001: Selection of Apache Arrow for Internal Zero-Copy Data Plane
- **Status**: Approved / Frozen
- **Context**: Streaming engines frequently suffer from serialization overhead and memory copying across operator boundaries.
- **Decision**: Platform 1 adopts Apache Arrow C++ IPC memory format as its internal binary representation. In-memory data transfer between operators uses reference-counted Arrow buffer slices ($O(1)$ memory slicing with zero heap copying).
- **Consequences**: Unlocks 10M+ records/sec throughput for vectorized micro-batching. Requires custom PyArrow memory pool bridges to prevent off-heap leaks.

### ADR-002: Dual Hybrid Execution Runtime (Record vs. Micro-Batch)
- **Status**: Approved / Frozen
- **Context**: Applications demand both sub-millisecond event processing latencies and high-throughput bulk processing.
- **Decision**: Platform 1 implements a dual-mode engine. Record-by-record mode processes individual tuples for sub-millisecond latencies (< 1ms), while Micro-batch mode groups tuples into Arrow batches for maximum SIMD throughput.
- **Consequences**: Increases execution runtime complexity, managed by a clean `ExecutionPlanner` facade.

### ADR-003: Asynchronous Barrier Snapshotting (Chandy-Lamport Variant)
- **Status**: Approved / Frozen
- **Context**: Distributed streaming state requires consistent checkpoints without locking processing threads.
- **Decision**: Injects lightweight `CheckpointBarrier` control records into stream channels. Operators align barriers across input channels before taking incremental local state snapshots.
- **Consequences**: Enables deterministic exactly-once processing with non-blocking stream ingestion.

### ADR-004: Decoupled State Backend Abstraction (`IStateBackend`)
- **Status**: Approved / Frozen
- **Context**: Hardcoding RocksDB or In-Memory storage limits deployment flexibility in constrained environments.
- **Decision**: All operator state access passes through `IStateBackend` interface. Standard implementations include `InMemoryStateBackend`, `RocksDBStateBackend`, and `RedisStateBackend`.
- **Consequences**: Allows zero-dependency testing with in-memory backends and petabyte-scale production storage with RocksDB.

### ADR-005: Multi-Tier Stream Graph Lowering & Operator Compiler
- **Status**: Approved / Frozen
- **Context**: Monolithic pipeline fusion limits opportunities for global graph optimization, predicate pushdowns, and operator reordering.
- **Decision**: Introduces explicit lowering: `LogicalStreamGraph` $\rightarrow$ `OptimizedStreamGraph` $\rightarrow$ `PhysicalStreamGraph` $\rightarrow$ `ExecutionGraph`. An `OperatorCompiler` fuses and inlines linear operator chains into specialized execution kernels.
- **Consequences**: Provides query-engine-grade optimization for generic stream topologies.

---

## 3. Stream Graph Architecture & Operator Compiler

Platform 1 structures stream pipeline transformation across four explicit lowering stages:

```
                  ┌──────────────────────────────┐
                  │    LogicalStreamGraph        │
                  └──────────────┬───────────────┘
                                 │
                                 ▼ (GraphOptimizer: RBO / CBO Rules)
                  ┌──────────────────────────────┐
                  │   OptimizedStreamGraph       │
                  └──────────────┬───────────────┘
                                 │
                                 ▼ (OperatorCompiler: Fusion & Inlining)
                  ┌──────────────────────────────┐
                  │    PhysicalStreamGraph       │
                  └──────────────┬───────────────┘
                                 │
                                 ▼ (ExecutionPlanner: Task Binding)
                  ┌──────────────────────────────┐
                  │       ExecutionGraph         │
                  └──────────────────────────────┘
```

### 1. LogicalStreamGraph
Represents the user-defined streaming topology DAG without execution details. Vertices represent generic logical operations (Source, Filter, Map, Window, Join, Sink).

### 2. OptimizedStreamGraph
Produced by the `GraphOptimizer`. Applies rule-based optimizations (operator reordering, predicate pushdown, redundant project elimination) and cost-based optimizations (partitioning cost, window memory cost).

### 3. PhysicalStreamGraph
Generated by the `OperatorCompiler`. Linear sequences of element-wise operators are fused into single `FusedOperatorKernel` vertices. Vectorized kernels are assigned based on stream throughput heuristics.

### 4. ExecutionGraph
The final runnable topology constructed by `ExecutionPlanner`. Maps physical vertices to parallel `TaskDriver` workers, instantiates lock-free `RingBufferQueue` channels, binds memory pools, and assigns thread affinities.

---

## 4. Graph Optimizer & Optimization Engine

The `GraphOptimizer` (`akaal.platform.streaming.optimizer`) executes transformation rules prior to compilation.

```python
# akaal/platform/streaming/optimizer/graph_optimizer.py
from abc import ABC, abstractmethod
from typing import List
from akaal.platform.streaming.graph.logical_graph import LogicalStreamGraph

class IOptimizerRule(ABC):
    @abstractmethod
    def apply(self, graph: LogicalStreamGraph) -> LogicalStreamGraph:
        pass

class PredicatePushdownRule(IOptimizerRule):
    """Pushes filter predicates upstream closer to stream sources."""
    def apply(self, graph: LogicalStreamGraph) -> LogicalStreamGraph:
        # Reorder Filter -> Map to Filter-upstream if Map does not affect filter columns
        return graph

class OperatorFusionPlannerRule(IOptimizerRule):
    """Groups adjacent element-wise transformations into fusion candidate blocks."""
    def apply(self, graph: LogicalStreamGraph) -> LogicalStreamGraph:
        return graph

class GraphOptimizer:
    """Executes rule-based (RBO) and cost-based (CBO) graph optimizations."""
    def __init__(self, rules: List[IOptimizerRule]) -> None:
        self._rules = rules

    def optimize(self, logical_graph: LogicalStreamGraph) -> LogicalStreamGraph:
        current_graph = logical_graph
        for rule in self._rules:
            current_graph = rule.apply(current_graph)
        return current_graph
```

---

## 5. Execution Planner & Physical Execution Plan

The `ExecutionPlanner` (`akaal.platform.streaming.planner`) decouples graph resolution from execution runtime.

```python
# akaal/platform/streaming/planner/execution_planner.py
from dataclasses import dataclass
from typing import List, Dict, Any
from akaal.platform.streaming.graph.physical_graph import PhysicalStreamGraph
from akaal.platform.streaming.api.config import StreamConfig

@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    """Immutable, fully-resolved physical execution topology blueprint."""
    job_id: str
    physical_graph: PhysicalStreamGraph
    task_vertex_configs: Dict[str, Any]
    channel_capacities: Dict[str, int]
    allocated_memory_bytes: int

class ExecutionPlanner:
    """Lowers physical stream graph into runnable ExecutionPlan."""
    def __init__(self, config: StreamConfig) -> None:
        self._config = config

    def create_plan(self, job_id: str, physical_graph: PhysicalStreamGraph) -> ExecutionPlan:
        # Calculate parallelism, buffer sizes, memory pool allocations
        return ExecutionPlan(
            job_id=job_id,
            physical_graph=physical_graph,
            task_vertex_configs={},
            channel_capacities={},
            allocated_memory_bytes=self._config.max_memory_bytes
        )
```

---

## 6. Repository Structure

Platform 1 Part 1 resides in `akaal/platform/streaming/`.

```
temp_akaal-main/
├── akaal/
│   ├── platform/
│   │   └── streaming/                 # Platform 1 Root Package Namespace
│   │       ├── advisor/               # Performance Advisor & Recommendation Engine
│   │       ├── api/                   # Public Facades & Client Builders
│   │       ├── buffer/                # Zero-Copy Buffers & Memory Allocators
│   │       ├── checkpoint/            # Barrier Snapshots & Checkpoint Coordinator
│   │       ├── common/                # Shared Primitives, Clock & Serialization
│   │       ├── compiler/              # Operator Compiler & Pipeline Lowering
│   │       ├── diagnostics/           # Memory & Buffer Diagnostic Suites
│   │       ├── exceptions/            # Standardized Exception Hierarchy
│   │       ├── execution/             # Hybrid Runtime, Micro-Batch & Record Streaming
│   │       ├── graph/                 # Logical, Physical & Execution Stream Graphs
│   │       ├── inspector/             # Live Runtime Inspector & Debugger
│   │       ├── interfaces/            # Structural Protocols & Abstract Contracts
│   │       ├── joins/                 # Adaptive Join Engine (Hash, Sort-Merge, Nested)
│   │       ├── lifecycle/             # Centralized Operator Lifecycle Manager
│   │       ├── memory/                # Arrow Allocator Bridge & Memory Pools
│   │       ├── metrics/               # Streaming Metrics Registry & Exporters
│   │       ├── models/                # Immutable Stream Payloads & Arrow Batches
│   │       ├── operators/             # Streaming Operators & Fused Kernels
│   │       ├── optimizer/             # Logical Graph Optimizer (RBO / CBO)
│   │       ├── planner/               # Execution Planner & ExecutionPlan Builders
│   │       ├── plugins/               # Sandboxed Plugin Registry & Loader
│   │       ├── queue/                 # Lock-Free Ring Queues & Backpressure
│   │       ├── recovery/              # State Recovery Engine & WAL Readers
│   │       ├── resources/             # Centralized Resource & Admission Manager
│   │       ├── scheduling/            # Adaptive & Core-Pinned Work-Stealing Scheduler
│   │       ├── security/              # Enclave Isolation & Transport Cipher
│   │       ├── serialization/         # Unified Serialization Registry (Arrow/JSON/Proto)
│   │       ├── state/                 # State Backend Abstractions (RocksDB/Redis/RAM)
│   │       ├── state_machine/         # Lifecycle State Controllers
│   │       ├── watermarks/            # Event-Time Clock & Watermark Engine
│   │       └── windows/               # Tumbling, Sliding, Session Window Engines
```

---

## 7. Folder Layout

Complete layout containing all 92 Python modules across 31 packages:

```
akaal/platform/streaming/
├── __init__.py
├── advisor/
│   ├── __init__.py
│   ├── optimization_rules.py
│   └── performance_advisor.py
├── api/
│   ├── __init__.py
│   ├── client.py
│   ├── config.py
│   ├── context.py
│   └── environment.py
├── buffer/
│   ├── __init__.py
│   ├── allocator.py
│   ├── arrow_slice.py
│   ├── ring_buffer.py
│   ├── shared_memory.py
│   └── zero_copy.py
├── checkpoint/
│   ├── __init__.py
│   ├── barrier.py
│   ├── coordinator.py
│   ├── snapshot.py
│   └── storage.py
├── common/
│   ├── __init__.py
│   ├── clock.py
│   ├── id_generator.py
│   └── types.py
├── compiler/
│   ├── __init__.py
│   ├── fusion_compiler.py
│   ├── inlining.py
│   └── operator_compiler.py
├── diagnostics/
│   ├── __init__.py
│   ├── buffer_analyzer.py
│   ├── copy_detector.py
│   ├── leak_detector.py
│   ├── memory_profiler.py
│   └── spill_analyzer.py
├── exceptions/
│   ├── __init__.py
│   ├── buffer_exceptions.py
│   ├── execution_exceptions.py
│   └── streaming_exceptions.py
├── execution/
│   ├── __init__.py
│   ├── hybrid_runtime.py
│   ├── micro_batch.py
│   ├── record_stream.py
│   └── task_driver.py
├── graph/
│   ├── __init__.py
│   ├── execution_graph.py
│   ├── logical_graph.py
│   └── physical_graph.py
├── inspector/
│   ├── __init__.py
│   ├── live_debugger.py
│   └── runtime_inspector.py
├── interfaces/
│   ├── __init__.py
│   ├── buffer_interface.py
│   ├── operator_interface.py
│   ├── plugin_interface.py
│   └── state_interface.py
├── joins/
│   ├── __init__.py
│   ├── adaptive_join.py
│   ├── hash_join.py
│   ├── nested_loop_join.py
│   └── sort_merge_join.py
├── lifecycle/
│   ├── __init__.py
│   ├── lifecycle_manager.py
│   └── operator_states.py
├── memory/
│   ├── __init__.py
│   ├── allocator_bridge.py
│   ├── memory_pool.py
│   └── quota_manager.py
├── metrics/
│   ├── __init__.py
│   ├── opentelemetry_exporter.py
│   ├── prometheus_exporter.py
│   └── streaming_metrics_registry.py
├── models/
│   ├── __init__.py
│   ├── arrow_batch.py
│   ├── event_record.py
│   ├── stream_payload.py
│   └── watermark_record.py
├── operators/
│   ├── __init__.py
│   ├── base_operator.py
│   ├── filter_operator.py
│   ├── fused_operator.py
│   ├── map_operator.py
│   └── sink_operator.py
├── optimizer/
│   ├── __init__.py
│   ├── cost_model.py
│   ├── graph_optimizer.py
│   └── rules.py
├── planner/
│   ├── __init__.py
│   ├── execution_plan.py
│   └── execution_planner.py
├── plugins/
│   ├── __init__.py
│   ├── loader.py
│   ├── plugin_contract.py
│   └── registry.py
├── queue/
│   ├── __init__.py
│   ├── backpressure_controller.py
│   ├── credit_queue.py
│   └── ring_queue.py
├── recovery/
│   ├── __init__.py
│   ├── replay_engine.py
│   ├── state_recovery.py
│   └── WAL_reader.py
├── resources/
│   ├── __init__.py
│   ├── admission_control.py
│   └── resource_manager.py
├── scheduling/
│   ├── __init__.py
│   ├── adaptive_scheduler.py
│   ├── partition_assigner.py
│   ├── thread_pool.py
│   └── work_stealing.py
├── security/
│   ├── __init__.py
│   ├── payload_cipher.py
│   ├── resource_isolation.py
│   └── sandbox.py
├── serialization/
│   ├── __init__.py
│   ├── arrow_codec.py
│   ├── json_codec.py
│   ├── protobuf_codec.py
│   └── serialization_registry.py
├── state/
│   ├── __init__.py
│   ├── in_memory_backend.py
│   ├── redis_backend.py
│   ├── rocksdb_backend.py
│   └── state_backend_interface.py
├── state_machine/
│   ├── __init__.py
│   ├── execution_state.py
│   └── lifecycle_controller.py
├── watermarks/
│   ├── __init__.py
│   ├── bounded_out_of_orderness.py
│   ├── generator.py
│   └── watermark_assigner.py
└── windows/
    ├── __init__.py
    ├── custom_window.py
    ├── session_window.py
    ├── sliding_window.py
    ├── tumbling_window.py
    └── window_evaluator.py
```

---

## 8. Packages

| Package Name | Subsystem Ownership | Key Responsibility |
| :--- | :--- | :--- |
| `akaal.platform.streaming.advisor` | Performance Optimization | Emits live recommendations for batch size, fusion, and resource allocation. |
| `akaal.platform.streaming.api` | Client & Public Facades | Top-level execution environment setup, DAG construction, and client API. |
| `akaal.platform.streaming.buffer` | Zero-Copy Data Plane | Off-heap PyArrow allocations, ring buffer memory views, and shared memory IPC. |
| `akaal.platform.streaming.checkpoint` | Snapshot Coordinator | Chandy-Lamport barrier injection, alignment, snapshot storage, and ACK collection. |
| `akaal.platform.streaming.common` | Shared System Core | Epoch clocks, nanosecond timers, UUID v7 sequence generators, and type primitives. |
| `akaal.platform.streaming.compiler` | Pipeline Fusion & Lowering | Operator specialization, function inlining, and physical execution graph lowering. |
| `akaal.platform.streaming.diagnostics` | Diagnostics & Profiling | Leak detection, buffer lifetime analysis, copy tracking, and allocation heatmaps. |
| `akaal.platform.streaming.exceptions` | Exception Infrastructure | Standardized streaming error hierarchies and fault codes. |
| `akaal.platform.streaming.execution` | Runtime Drivers | Hybrid runtime orchestrator executing micro-batches or record streaming. |
| `akaal.platform.streaming.graph` | Topology Model Layer | Defines Logical, Physical, and Execution stream graphs. |
| `akaal.platform.streaming.inspector` | System Inspection | Real-time live inspection of threads, queues, memory pools, and operator states. |
| `akaal.platform.streaming.interfaces` | Interface Standards | Abstract contracts for operators, state backends, serializers, and resource managers. |
| `akaal.platform.streaming.joins` | Adaptive Stream Joins | Streaming Hash Join, Sort-Merge Join, and dynamic algorithm switching. |
| `akaal.platform.streaming.lifecycle` | Operator Governance | Centralized OperatorLifecycleManager managing 10 explicit operator states. |
| `akaal.platform.streaming.memory` | Memory Pool Core | Hierarchical memory pool tree overriding PyArrow C++ allocators. |
| `akaal.platform.streaming.metrics` | Observability Registry | Unified StreamingMetricsRegistry driving OpenTelemetry and Prometheus exporters. |
| `akaal.platform.streaming.models` | Data Structures | Immutable payload envelopes, Arrow record batches, and Watermark records. |
| `akaal.platform.streaming.operators` | Streaming Operators | Core transformation operators (Filter, Map, Project, FusedKernel, Sink). |
| `akaal.platform.streaming.optimizer` | Topology Optimization | Rule-Based (RBO) and Cost-Based (CBO) graph optimizer. |
| `akaal.platform.streaming.planner` | Execution Planning | Converts PhysicalStreamGraph into immutable execution plans. |
| `akaal.platform.streaming.plugins` | Plugin Framework | Sandboxed dynamic operator plugin loader and thread registry. |
| `akaal.platform.streaming.queue` | Inter-operator Queues | Lock-free SPSC ring buffers with credit-based backpressure. |
| `akaal.platform.streaming.recovery` | Fault Recovery | Write-Ahead-Log (WAL) reading, snapshot restoration, and replay alignment. |
| `akaal.platform.streaming.resources` | Resource Management | Centralized ResourceManager controlling CPU, memory, queues, priorities, and admission. |
| `akaal.platform.streaming.scheduling` | Task Scheduling | Core-pinned work-stealing and dynamic adaptive schedulers. |
| `akaal.platform.streaming.security` | Enclave Security | In-flight payload encryption (AES-256-GCM) and plugin process sandboxing. |
| `akaal.platform.streaming.serialization` | Serialization Registry | Centralized codec registry for Arrow, JSON, Protobuf, and raw bytes. |
| `akaal.platform.streaming.state` | State Backends | Decoupled state persistence (InMemory, RocksDB, Redis). |
| `akaal.platform.streaming.state_machine` | Engine State Control | Job-level execution state machine transition controllers. |
| `akaal.platform.streaming.watermarks` | Event-Time Engine | Out-of-order event-time watermark generators and aligners. |
| `akaal.platform.streaming.windows` | Streaming Windows | Tumbling, Sliding, Session, and Custom window evaluation engines. |

---

## 9. Modules

Exhaustive module catalog for all 92 Python files:

1. `advisor.performance_advisor`: Evaluates live engine metrics and outputs optimization recommendations.
2. `advisor.optimization_rules`: Rules for batch size tuning, fusion suggestions, and parallelism scaling.
3. `api.client`: Client driver interface for submitting and monitoring streaming execution jobs.
4. `api.config`: Immutable configuration dataclass for streaming DAG executions.
5. `api.context`: Execution context housing runtime environment parameters and task metadata.
6. `api.environment`: Top-level builder pattern for constructing streaming topologies.
7. `buffer.allocator`: C++ Arrow allocator wrapper with PyArrow bridge integration.
8. `buffer.arrow_slice`: Zero-copy $O(1)$ PyArrow RecordBatch slice operations.
9. `buffer.ring_buffer`: SPSC lock-free ring buffer memory allocation plane.
10. `buffer.shared_memory`: POSIX shared memory allocations for zero-copy inter-process communication.
11. `buffer.zero_copy`: Off-heap buffer reference counting and pointer wrapper primitives.
12. `checkpoint.barrier`: Control record carrying checkpoint sequence IDs across topologies.
13. `checkpoint.coordinator`: Manages snapshot alignment, barrier tracking, and storage commits.
14. `checkpoint.snapshot`: Incremental state snapshot data structure with SHA-256 integrity verification.
15. `checkpoint.storage`: Storage interface implementations (S3, RocksDB, POSIX filesystem).
16. `common.clock`: Monotonic nanosecond system clock for precise event timing.
17. `common.id_generator`: High-throughput sequence number and UUID v7 generator.
18. `common.types`: Primitive types (StreamID, PartitionID, WatermarkTimestamp, SequenceNumber).
19. `compiler.fusion_compiler`: Groups adjacent operators into unified single-pass loops.
20. `compiler.inlining`: Inlines scalar map/filter functions into vectorized Arrow kernels.
21. `compiler.operator_compiler`: Main compiler lowering physical stream graph into executable kernels.
22. `diagnostics.buffer_analyzer`: Inspects buffer occupancy, allocation velocity, and capacity limits.
23. `diagnostics.copy_detector`: Traverses processing pipeline to flag unexpected memory copy operations.
24. `diagnostics.leak_detector`: Tracks unreleased Arrow memory buffers across system pools.
25. `diagnostics.memory_profiler`: Generates realtime memory heap profiles and allocation graphs.
26. `diagnostics.spill_analyzer`: Monitors NVMe spill disk write bandwidth and state eviction counts.
27. `exceptions.buffer_exceptions`: Buffer overflow and memory allocation error definitions.
28. `execution_exceptions.py`: Topology execution, deadlock, and pipeline failure errors.
29. `streaming_exceptions.py`: Base exception class for all streaming subsystem errors.
30. `execution.hybrid_runtime`: Orchestrator managing dynamic execution between batch and record modes.
31. `execution.micro_batch`: Vectorized batch task driver executing PyArrow kernels.
32. `execution.record_stream`: Sub-millisecond element-by-element streaming task driver.
33. `execution.task_driver`: Runnable worker execution thread assigned to an execution graph vertex.
34. `graph.execution_graph`: Runnable execution topology with task vertices and channels.
35. `graph.logical_graph`: User-defined logical stream topology DAG representation.
36. `graph.physical_graph`: Fused and vectorized physical stream graph topology.
37. `inspector.live_debugger`: Live debugging interface for intercepting stream records in-flight.
38. `inspector.runtime_inspector`: Live introspection API for inspecting threads, memory, and state.
39. `interfaces.buffer_interface`: Protocol specifying zero-copy buffer operations.
40. `interfaces.operator_interface`: Structural contract for streaming operators (`open`, `process`, `close`).
41. `interfaces.plugin_interface`: Structural protocol for external dynamic operator plugins.
42. `interfaces.state_interface`: Contract for key-value, list, and window state stores.
43. `joins.adaptive_join`: Adaptive join engine toggling between hash, sort-merge, and nested loop joins.
44. `joins.hash_join`: Symmetric in-memory streaming hash join implementation.
45. `joins.nested_loop_join`: Fallback nested-loop join for non-equi join predicates.
46. `joins.sort_merge_join`: External-memory-bounded streaming sort-merge join implementation.
47. `lifecycle.lifecycle_manager`: Centralized manager governing operator lifecycle transitions.
48. `lifecycle.operator_states`: Enumeration of explicit operator lifecycle states.
49. `memory.allocator_bridge`: PyArrow C++ memory pool bridge forwarding allocations to custom pools.
50. `memory.memory_pool`: Hierarchical memory pool tree enforcing strict allocation limits.
51. `memory.quota_manager`: Monitors memory quotas and triggers dynamic backpressure alerts.
52. `metrics.opentelemetry_exporter`: Emits OpenTelemetry trace spans and metric histograms.
53. `metrics.prometheus_exporter`: Exposes HTTP scraping endpoint for Prometheus metrics.
54. `metrics.streaming_metrics_registry`: Centralized metric registry for counters, gauges, and timers.
55. `models.arrow_batch`: Immutable typed wrapper around `pyarrow.RecordBatch`.
56. `models.event_record`: Container holding event key, payload, timestamp, and headers.
57. `models.stream_payload`: Unified payload container for Arrow, JSON, Protobuf, or bytes.
58. `models.watermark_record`: Control record propagating event-time progress across channels.
59. `operators.base_operator`: Abstract base class for all stream operators.
60. `operators.filter_operator`: Boolean filter evaluation operator.
61. `operators.fused_operator`: Fused pipeline execution container for element-wise operators.
62. `operators.map_operator`: Element-wise transformation and projection operator.
63. `operators.sink_operator`: Terminal streaming vertex writing to external sinks.
64. `optimizer.cost_model`: Cost model estimating CPU, memory, and partitioning cost for DAGs.
65. `optimizer.graph_optimizer`: Optimizer applying RBO and CBO optimization rules.
66. `optimizer.rules`: Collection of optimization rules (PredicatePushdown, OperatorReordering).
67. `planner.execution_plan`: Immutable dataclass representing a fully-resolved execution blueprint.
68. `planner.execution_planner`: Converts physical graph into executable `ExecutionPlan`.
69. `plugins.loader`: Dynamic module loader importing and verifying third-party plugins.
70. `plugins.plugin_contract`: Interface contract and manifest schema for external plugins.
71. `plugins.registry`: Singleton registry mapping plugin names to operator factories.
72. `queue.backpressure_controller`: Manages channel fill ratios and regulates upstream throttles.
73. `queue.credit_queue`: Credit-based flow control queue for inter-thread streaming channels.
74. `queue.ring_queue`: Fixed-capacity lock-free SPSC ring queue implementation.
75. `recovery.replay_engine`: Reconstructs state by replaying stream WAL records from checkpoint offsets.
76. `recovery.state_recovery`: Restores local operator states from snapshot storage stores.
77. `recovery.WAL_reader`: High-performance binary reader for Write-Ahead Log segment files.
78. `resources.admission_control`: Enforces topology submission admission policies based on cluster capacity.
79. `resources.resource_manager`: Central manager allocating CPU, memory, queues, priorities, and tokens.
80. `scheduling.adaptive_scheduler`: Dynamically adjusts worker thread allocation based on system load.
81. `scheduling.partition_assigner`: Assigns stream partitions to worker threads for core affinity.
82. `scheduling.thread_pool`: Core-pinned worker thread pool for topology execution.
83. `scheduling.work_stealing`: Work-stealing queue scheduler minimizing thread starvation.
84. `security.payload_cipher`: Encrypts/decrypts in-transit stream payloads using AES-256-GCM.
85. `security.resource_isolation`: Sandboxes process and Cgroup limits for operator tasks.
86. `security.sandbox`: Restricts plugin access to OS syscalls and network interfaces.
87. `serialization.arrow_codec`: Zero-copy encoder/decoder for Apache Arrow RecordBatches.
88. `serialization.json_codec`: Fast JSON stream payload serializer using simdjson.
89. `serialization.protobuf_codec`: Zero-copy Protobuf stream payload serializer.
90. `serialization.serialization_registry`: Centralized registry mapping formats to codecs.
91. `state.in_memory_backend`: Fast non-persistent in-memory state backend for testing/ephemeral jobs.
92. `state.redis_backend`: Remote state backend backed by Redis cluster storage.
93. `state.rocksdb_backend`: Embedded key-value state backend backed by local RocksDB engine.
94. `state.state_backend_interface`: Protocol defining `IStateBackend` contract.
95. `state_machine.execution_state`: Job lifecycle state machine transitions.
96. `state_machine.lifecycle_controller`: Manages valid transitions between execution states.
97. `watermarks.bounded_out_of_orderness`: Watermark generator allowing configured max latency delay.
98. `watermarks.generator`: Abstract protocol for custom event-time watermark generators.
99. `watermarks.watermark_assigner`: Operator extracting event timestamps and emitting watermarks.
100. `windows.custom_window`: User-defined window assigner and trigger evaluator.
101. `windows.session_window`: Dynamic gap-based session window engine with window merging.
102. `windows.sliding_window`: Overlapping fixed-size time window engine.
103. `windows.tumbling_window`: Non-overlapping fixed-size time window engine.
104. `windows.window_evaluator`: Triggers window function execution upon watermark arrival.

---

## 10. File Ownership & Responsibility Matrix

Every file in `akaal/platform/streaming/` is assigned a strict team ownership domain:

```
[Core Architecture & API Team]
├── api/ (client.py, config.py, context.py, environment.py)
├── common/ (clock.py, id_generator.py, types.py)
├── graph/ (logical_graph.py, physical_graph.py, execution_graph.py)
├── planner/ (execution_plan.py, execution_planner.py)
└── exceptions/ (buffer_exceptions.py, execution_exceptions.py, streaming_exceptions.py)

[Compiler & Optimization Engine Team]
├── compiler/ (fusion_compiler.py, inlining.py, operator_compiler.py)
├── optimizer/ (cost_model.py, graph_optimizer.py, rules.py)
└── operators/ (base_operator.py, filter_operator.py, fused_operator.py, map_operator.py, sink_operator.py)

[Memory, Buffers & Diagnostics Team]
├── buffer/ (allocator.py, arrow_slice.py, ring_buffer.py, shared_memory.py, zero_copy.py)
├── memory/ (allocator_bridge.py, memory_pool.py, quota_manager.py)
└── diagnostics/ (buffer_analyzer.py, copy_detector.py, leak_detector.py, memory_profiler.py, spill_analyzer.py)

[Resource, Scheduling & Concurrency Team]
├── queue/ (backpressure_controller.py, credit_queue.py, ring_queue.py)
├── resources/ (admission_control.py, resource_manager.py)
└── scheduling/ (adaptive_scheduler.py, partition_assigner.py, thread_pool.py, work_stealing.py)

[State, Checkpoint & Reliability Team]
├── checkpoint/ (barrier.py, coordinator.py, snapshot.py, storage.py)
├── recovery/ (replay_engine.py, state_recovery.py, WAL_reader.py)
├── state/ (in_memory_backend.py, redis_backend.py, rocksdb_backend.py, state_backend_interface.py)
└── lifecycle/ (lifecycle_manager.py, operator_states.py)

[Stream Algorithms, Windows & Joins Team]
├── joins/ (adaptive_join.py, hash_join.py, nested_loop_join.py, sort_merge_join.py)
├── watermarks/ (bounded_out_of_orderness.py, generator.py, watermark_assigner.py)
└── windows/ (custom_window.py, session_window.py, sliding_window.py, tumbling_window.py, window_evaluator.py)

[Observability, Security & Tooling Team]
├── advisor/ (optimization_rules.py, performance_advisor.py)
├── inspector/ (live_debugger.py, runtime_inspector.py)
├── metrics/ (opentelemetry_exporter.py, prometheus_exporter.py, streaming_metrics_registry.py)
├── plugins/ (loader.py, plugin_contract.py, registry.py)
├── security/ (payload_cipher.py, resource_isolation.py, sandbox.py)
└── serialization/ (arrow_codec.py, json_codec.py, protobuf_codec.py, serialization_registry.py)
```

---

## 11. Core Interface Contracts & Protocols

```python
# akaal/platform/streaming/state/state_backend_interface.py
from typing import Protocol, Optional, Any

class IStateBackend(Protocol):
    """Abstract interface for all persistent and in-memory state backends."""

    def open(self, job_id: str, operator_id: str) -> None: ...
    def get_value(self, key: bytes) -> Optional[bytes]: ...
    def put_value(self, key: bytes, value: bytes) -> None: ...
    def delete_value(self, key: bytes) -> None: ...
    def create_snapshot(self, checkpoint_id: int) -> bytes: ...
    def restore_snapshot(self, checkpoint_id: int, snapshot_bytes: bytes) -> None: ...
    def close(self) -> None: ...
```

```python
# akaal/platform/streaming/serialization/serialization_registry.py
from typing import Protocol, Dict, Type, Any

class IStreamCodec(Protocol):
    def encode(self, obj: Any) -> bytes: ...
    def decode(self, data: bytes) -> Any: ...

class SerializationRegistry:
    """Centralized registry managing format codecs (Arrow, JSON, Protobuf)."""

    _codecs: Dict[str, IStreamCodec] = {}

    @classmethod
    def register_codec(cls, format_name: str, codec: IStreamCodec) -> None:
        cls._codecs[format_name.lower()] = codec

    @classmethod
    def get_codec(cls, format_name: str) -> IStreamCodec:
        format_key = format_name.lower()
        if format_key not in cls._codecs:
            raise KeyError(f"Codec format '{format_name}' not registered in SerializationRegistry.")
        return cls._codecs[format_key]
```

---

## 12. Centralized Operator Lifecycle Manager

Operators transition through 10 explicit lifecycle states managed centrally by `OperatorLifecycleManager` (`akaal.platform.streaming.lifecycle`).

```
[CREATED] ──► [INITIALIZED] ──► [OPEN] ──► [RUNNING] ──► [STOPPING] ──► [STOPPED] ──► [DESTROYED]
                                 │▲             │▲             │
                                 ││             ││             ▼
                         CHECKPOINTING       RESTORING     [FAILED]
```

```python
# akaal/platform/streaming/lifecycle/operator_states.py
from enum import Enum, auto

class OperatorState(Enum):
    CREATED = auto()
    INITIALIZED = auto()
    OPEN = auto()
    RUNNING = auto()
    CHECKPOINTING = auto()
    RESTORING = auto()
    STOPPING = auto()
    STOPPED = auto()
    FAILED = auto()
    DESTROYED = auto()
```

---

## 13. Resource Manager & Admission Control

The `ResourceManager` (`akaal.platform.streaming.resources`) governs cluster-wide CPU core allocations, off-heap memory, ring buffer capacities, execution tokens, and job admission control.

```python
# akaal/platform/streaming/resources/resource_manager.py
from dataclasses import dataclass
from threading import Lock
from akaal.platform.streaming.exceptions.execution_exceptions import ResourceAdmissionError

@dataclass
class ResourceQuota:
    cpu_cores: int
    memory_bytes: int
    ring_buffer_slots: int

class ResourceManager:
    """Central manager governing resource allocation and topology admission control."""

    def __init__(self, total_quota: ResourceQuota) -> None:
        self._total_quota = total_quota
        self._allocated = ResourceQuota(0, 0, 0)
        self._lock = Lock()

    def request_admission(self, required: ResourceQuota) -> bool:
        with self._lock:
            if (self._allocated.cpu_cores + required.cpu_cores > self._total_quota.cpu_cores or
                self._allocated.memory_bytes + required.memory_bytes > self._total_quota.memory_bytes):
                raise ResourceAdmissionError("Topology admission rejected: Cluster capacity exceeded.")
            
            self._allocated.cpu_cores += required.cpu_cores
            self._allocated.memory_bytes += required.memory_bytes
            self._allocated.ring_buffer_slots += required.ring_buffer_slots
            return True

    def release_resources(self, released: ResourceQuota) -> None:
        with self._lock:
            self._allocated.cpu_cores = max(0, self._allocated.cpu_cores - released.cpu_cores)
            self._allocated.memory_bytes = max(0, self._allocated.memory_bytes - released.memory_bytes)
            self._allocated.ring_buffer_slots = max(0, self._allocated.ring_buffer_slots - released.ring_buffer_slots)
```

---

## 14. Memory & Buffer Diagnostics Suite

### 1. Memory Profiler & Leak Detector (`akaal.platform.streaming.diagnostics.memory_profiler`)
- **Heap Graph Tracking**: Periodically snapshots PyArrow off-heap pointer maps.
- **Leak Detector**: Emits warning alerts if PyArrow atomic reference counters remain non-zero for disposed record batches after 30 seconds.
- **Fragmentation Detector**: Calculates physical vs. allocated memory ratio to detect RSS fragmentation spikes.

### 2. Buffer & Copy Analyzer (`akaal.platform.streaming.diagnostics.buffer_analyzer`)
- **Copy Detector**: Intercepts stream record transfers across operator boundaries to verify zero byte copy operations.
- **Allocation Heatmap**: Generates realtime visual heatmaps of SPSC ring buffer depth and memory pool utilization.
- **Spill Analyzer**: Tracks NVMe SSD spill write bandwidth, eviction rates, and I/O wait latency.

---

## 15. Adaptive Scheduler

The `AdaptiveScheduler` (`akaal.platform.streaming.scheduling.adaptive_scheduler`) dynamically tunes core execution parameters based on real-time feedback loops.

```python
# akaal/platform/streaming/scheduling/adaptive_scheduler.py
from typing import Dict, Any

class AdaptiveScheduler:
    """Dynamically tunes thread affinity and execution mode based on system load."""

    def __init__(self, work_stealing_pool: Any) -> None:
        self._pool = work_stealing_pool

    def evaluate_and_adapt(self, metrics_snapshot: Dict[str, Any]) -> None:
        cpu_load = metrics_snapshot.get("cpu_load", 0.0)
        backpressure_ratio = metrics_snapshot.get("max_backpressure_ratio", 0.0)
        watermark_delay = metrics_snapshot.get("watermark_delay_ms", 0)

        # High backpressure & CPU headroom: Allocate additional worker threads
        if backpressure_ratio > 0.8 and cpu_load < 0.7:
            self._pool.expand_thread_pool(delta_threads=2)
        # Low load: Scale down threads to minimize CPU core thrashing
        elif backpressure_ratio < 0.1 and cpu_load < 0.2:
            self._pool.shrink_thread_pool(delta_threads=1)
```

---

## 16. Unified Streaming Metrics Registry

The `StreamingMetricsRegistry` (`akaal.platform.streaming.metrics`) provides atomic metric aggregation exported directly via OpenTelemetry traces and Prometheus endpoints.

```python
# akaal/platform/streaming/metrics/streaming_metrics_registry.py
from typing import Dict, Any
from threading import Lock

class StreamingMetricsRegistry:
    """Centralized metrics registry for counters, gauges, histograms, and timers."""

    def __init__(self) -> None:
        self._counters: Dict[str, int] = {}
        self._gauges: Dict[str, float] = {}
        self._lock = Lock()

    def increment_counter(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + value

    def set_gauge(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = value

    def collect_all(self) -> Dict[str, Any]:
        with self._lock:
            return {"counters": dict(self._counters), "gauges": dict(self._gauges)}
```

---

## 17. Runtime Inspector & Performance Advisor

### 1. Runtime Inspector (`akaal.platform.streaming.inspector`)
Exposes live introspective HTTP endpoints (`/debug/topology`, `/debug/queues`, `/debug/memory`) allowing operators to inspect live task thread states, queue fill ratios, memory pool allocations, and watermark progress without pausing execution.

### 2. Performance Advisor (`akaal.platform.streaming.advisor`)
Evaluates engine telemetries and generates automated, actionable performance optimization recommendations:
- *Recommendation Example*: "Operator `Filter_2` and `Map_3` exhibit 99% linear pipeline affinity. Enable Operator Fusion to reduce context-switching latency by an estimated 32%."
- *Recommendation Example*: "Window join state memory utilization reached 82%. Increase `Window Memory Pool` capacity or decrease tumbling window size from 60s to 30s."

---

## 18. Definition of Done (Version 3.0)

The implementation of **Platform 1 Part 1: Generic Streaming Execution Engine** is defined as officially COMPLETE when:

1. All 104 specified modules across 31 packages are fully implemented under `akaal/platform/streaming/`.
2. Static type checker `mypy --strict akaal/platform/streaming` returns 0 errors.
3. Test suite coverage reaches 100% across unit, integration, chaos, and performance benchmark suites.
4. Stream Graph 4-stage lowering (`LogicalStreamGraph` $\rightarrow$ `OptimizedStreamGraph` $\rightarrow$ `PhysicalStreamGraph` $\rightarrow$ `ExecutionGraph`) operates deterministically.
5. All 15 mandatory ARB enhancements are fully integrated and verified.
6. Zero-copy Arrow pipeline achieves > 10M records/sec in micro-batch mode and < 0.8ms p99 latency in record mode.
7. Asynchronous Chandy-Lamport barrier checkpointing and state replay engines pass exactly-once fault recovery tests across `InMemory`, `RocksDB`, and `Redis` state backends.
8. The Architecture Review Board (ARB) officially signs off on the final release certification report.
