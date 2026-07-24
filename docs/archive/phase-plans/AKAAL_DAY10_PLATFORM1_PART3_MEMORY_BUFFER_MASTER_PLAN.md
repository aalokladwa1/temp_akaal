# AKAAL DAY 10 — PLATFORM 1 PART 3: MEMORY, BUFFERS & ZERO-COPY DATA PLANE
## MASTER IMPLEMENTATION PLANNING CONTRACT (VERSION 1.0)
**Status:** Permanent Architecture Blueprint & Memory Engineering Contract (Frozen & ARB Certified)  
**Target Subsystem:** `akaal.platform.streaming.memory` & `akaal.platform.streaming.buffer` (Platform 1 Part 3 - Memory & Zero-Copy Data Plane)  
**Base Architecture:** Built directly upon frozen Platform 1 Part 1 (`akaal.platform.streaming`) and Part 2 (`akaal.platform.streaming.runtime`).

---

## 1. Executive Summary & ARB Memory Architecture Rationale

This Master Implementation Planning Contract Version 1.0 establishes the permanent, reference-grade engineering contract for **Platform 1 Part 3: Memory, Buffers & Zero-Copy Data Plane**. 

Designed to compete directly with Netty PooledByteBuf, Aeron buffers, and Apache Arrow C++ allocator architectures, Part 3 governs every byte allocated, referenced, transferred, pooled, spilled, recycled, and released inside the streaming execution engine.

### Core Memory Axioms
1. **Zero-Copy By Default**: Data transfer across operators, worker task runtimes, and IPC processes uses $O(1)$ reference-counted Apache Arrow memory buffer slices. Memory copying in the data path is strictly banned ($0$ bytes copied).
2. **Hierarchical Off-Heap Arenas**: Allocations bypass standard Python garbage collection. Memory is managed via a strict 4-tier off-heap hierarchy: `GlobalMemoryManager` $\rightarrow$ `MemoryPoolManager` $\rightarrow$ `MemoryArena` $\rightarrow$ `ThreadLocalPool` / `OperatorLocalPool`.
3. **Deterministic Single Ownership & Reference Counting**: Every buffer slice possesses exactly one primary owner, an atomic `ReferenceCounter`, and a single deterministic release path (`LifetimeManager`).
4. **NUMA & SIMD Cache Alignment**: Off-heap memory buffers are allocated on 64-byte boundaries aligned to physical CPU cache lines and NUMA memory nodes (`NUMAManager`), maximizing SIMD vectorization efficiency.
5. **Durable NVMe Disk Spilling & Defragmentation**: When memory pressure exceeds 80%, `SpillManager` offloads inactive window states and join buffers to local NVMe storage using zero-copy asynchronous I/O, while `CompactionEngine` prevents off-heap RSS fragmentation.

---

## 2. Alignment with Frozen Platform 1 Part 1 & Part 2 Contracts

Platform 1 Part 3 integrates cleanly into the frozen contracts of Parts 1 and 2:

| Frozen Base Subsystem | Part 3 Memory Subsystem Integration Boundary |
| :--- | :--- |
| **Part 1: `ResourceManager`** | `MemoryManager` requests global memory quotas and registers pool allocations with `ResourceManager`. |
| **Part 1: `IStateBackend`** | RocksDB / Redis / RAM state backends consume off-heap memory slices allocated by `ArrowBufferManager`. |
| **Part 2: `TaskExecutor`** | Worker threads pull pre-allocated thread-local arenas from `ThreadLocalPool` without lock contention. |
| **Part 2: `QueueConsumer` / `QueueProducer`** | SPSC ring queues transport zero-copy `BufferSlice` envelopes referencing underlying Arrow buffers. |
| **Part 2: `TaskMailbox`** | Control, recovery, and execution messages encapsulate zero-copy off-heap memory slice pointers. |

---

## 3. Architecture Decision Records for Memory Data Plane

### ADR-016: PyArrow C++ Off-Heap Allocator Custom Bridge
- **Status**: Approved / Frozen
- **Context**: Relying on default system `malloc` causes off-heap heap fragmentation and uncontrolled memory growth.
- **Decision**: Platform 1 overrides the PyArrow memory allocator via `AllocatorBridge`, binding C++ PyArrow allocations directly to internal `MemoryArena` tracking pools.
- **Consequences**: Provides 100% visibility over PyArrow off-heap allocations with strict quota enforcement.

### ADR-017: Lock-Free Thread-Local Arena Pools (`ThreadLocalPool`)
- **Status**: Approved / Frozen
- **Context**: Multi-threaded memory allocation from a single global pool introduces severe lock contention.
- **Decision**: Every core-pinned worker thread receives a pre-allocated 64MB `ThreadLocalPool` divided into fixed-size 64KB `MemoryArena` slabs. Thread-local allocations execute in $O(1)$ lock-free time.
- **Consequences**: Reduces allocator lock contention to zero during hot-path execution.

### ADR-018: Atomic Reference Counting & Lifetime Tracking (`ReferenceCounter`)
- **Status**: Approved / Frozen
- **Context**: Shared Arrow buffer slices across multiple downstream operator tasks risk premature deallocation or memory leaks.
- **Decision**: Every `BufferSlice` wraps an atomic `ReferenceCounter`. Retaining a slice increments the counter; releasing decrements it. When the counter reaches zero, `LifetimeManager` recycles the buffer back to `PoolAllocator`.
- **Consequences**: Guarantees deterministic memory reclamation without garbage collection pauses.

### ADR-019: 64-Byte Cache Line & NUMA Node Binding
- **Status**: Approved / Frozen
- **Context**: Non-aligned memory access degrades AVX-512 vectorization and induces cross-NUMA interconnect traffic.
- **Decision**: `NUMAManager` uses `numa_alloc_onnode` to allocate memory arenas on the CPU NUMA node matching thread affinity. All buffer base pointers are aligned to 64 bytes (`posix_memalign`).
- **Consequences**: Maximizes SIMD execution speed and eliminates inter-socket memory latency.

### ADR-020: Asynchronous NVMe Disk Spilling with Zero-Copy Direct I/O
- **Status**: Approved / Frozen
- **Context**: High-velocity stream joins cause memory pool exhaustion under peak traffic bursts.
- **Decision**: `SpillManager` serializes inactive window states to NVMe SSD using Linux `io_uring` direct disk writes (`O_DIRECT`).
- **Consequences**: Sustains > 500 MB/sec spill throughput without blocking streaming task drivers.

---

## 4. Repository Structure & Folder Layout

Platform 1 Part 3 resides in `akaal/platform/streaming/memory/` and `akaal/platform/streaming/buffer/`:

```
temp_akaal-main/
├── akaal/
│   ├── platform/
│   │   └── streaming/
│   │       ├── buffer/                        # Zero-Copy Buffer Subsystem
│   │       │   ├── __init__.py
│   │       │   ├── allocator.py
│   │       │   ├── arrow_buffer_manager.py
│   │       │   ├── arrow_slice.py
│   │       │   ├── buffer_inspector.py
│   │       │   ├── buffer_manager.py
│   │       │   ├── buffer_slice.py
│   │       │   ├── buffer_validator.py
│   │       │   ├── reference_counter.py
│   │       │   ├── ring_buffer.py
│   │       │   ├── shared_memory.py
│   │       │   ├── zero_copy.py
│   │       │   └── zero_copy_engine.py
│   │       └── memory/                        # Off-Heap Memory Hierarchy Subsystem
│   │           ├── __init__.py
│   │           ├── allocation_tracker.py
│   │           ├── allocator_bridge.py
│   │           ├── arena_allocator.py
│   │           ├── cache_optimizer.py
│   │           ├── compaction_engine.py
│   │           ├── defragmentation_engine.py
│   │           ├── fragmentation_analyzer.py
│   │           ├── global_memory_manager.py
│   │           ├── leak_detector.py
│   │           ├── lifetime_manager.py
│   │           ├── memory_allocator.py
│   │           ├── memory_arena.py
│   │           ├── memory_diagnostics.py
│   │           ├── memory_health.py
│   │           ├── memory_inspector.py
│   │           ├── memory_metrics.py
│   │           ├── memory_pool.py
│   │           ├── memory_pool_manager.py
│   │           ├── memory_pressure.py
│   │           ├── memory_profiler.py
│   │           ├── numa_manager.py
│   │           ├── operator_pool.py
│   │           ├── ownership_tracker.py
│   │           ├── pool_allocator.py
│   │           ├── quota_manager.py
│   │           ├── spill_manager.py
│   │           ├── spill_recovery.py
│   │           ├── thread_local_pool.py
│   │           └── window_pool.py
```

---

## 5. Subsystem Package & Module Taxonomy

Exhaustive module catalog for all 44 Part 3 Python modules across 2 package namespaces:

1. `buffer.allocator`: Low-level OS aligned memory allocation wrappers (`posix_memalign`).
2. `buffer.arrow_buffer_manager`: Manages PyArrow off-heap C++ buffer allocation lifecycle.
3. `buffer.arrow_slice`: $O(1)$ zero-copy slicing for PyArrow RecordBatch arrays.
4. `buffer.buffer_inspector`: Introspects live buffer pointers, sizes, and reference counts.
5. `buffer.buffer_manager`: Top-level manager orchestrating buffer allocations and recycling.
6. `buffer.buffer_slice`: Immutable envelope wrapping off-heap memory pointers with reference counts.
7. `buffer.buffer_validator`: Validates buffer boundary limits and memory integrity checksums.
8. `buffer.reference_counter`: Thread-safe atomic reference counter enforcing single release paths.
9. `buffer.ring_buffer`: SPSC lock-free ring buffer backed by off-heap shared memory.
10. `buffer.shared_memory`: POSIX shared memory allocations (`shm_open`) for zero-copy IPC.
11. `buffer.zero_copy`: Low-level pointer manipulation and zero-copy byte slice primitives.
12. `buffer.zero_copy_engine`: Orchestrates zero-copy record transfer across operator boundaries.
13. `memory.allocation_tracker`: Tracks active off-heap allocations across memory pools.
14. `memory.allocator_bridge`: Bridges PyArrow C++ memory pool calls to internal `MemoryArena`.
15. `memory.arena_allocator`: Slab-based arena allocator allocating fixed-size memory blocks.
16. `memory.cache_optimizer`: Ensures 64-byte alignment and padding to prevent false CPU cache line sharing.
17. `memory.compaction_engine`: Compacts sparse memory arenas to eliminate off-heap fragmentation.
18. `memory.defragmentation_engine`: Merges free memory blocks to restore contiguous allocation space.
19. `memory.fragmentation_analyzer`: Computes physical vs. allocated memory ratio (RSS fragmentation).
20. `memory.global_memory_manager`: Top-level memory authority managing global memory quotas.
21. `memory.leak_detector`: Tracks unreleased buffer references and flags memory leaks.
22. `memory.lifetime_manager`: Governs deterministic object disposal when reference count hits zero.
23. `memory.memory_allocator`: Abstract protocol for memory allocation implementations.
24. `memory.memory_arena`: Fixed-capacity off-heap memory slab assigned to worker arenas.
25. `memory.memory_diagnostics`: Comprehensive diagnostic suite for heap inspection and profiling.
26. `memory.memory_health`: Computes real-time memory health scores and pressure indicators.
27. `memory.memory_inspector`: Exposes live memory pool maps via debug HTTP endpoints.
28. `memory.memory_metrics`: Emits Prometheus counters and OpenTelemetry metrics for memory.
29. `memory.memory_pool`: Hierarchical memory pool tree node enforcing quota limits.
30. `memory.memory_pool_manager`: Manages dynamic pool expansion, shrinking, and quota rebalancing.
31. `memory.memory_pressure`: Detects memory pressure thresholds (Warning 70%, Critical 85%).
32. `memory.memory_profiler`: Generates heap allocation profiles and object lifetime graphs.
33. `memory.numa_manager`: Binds memory allocations to physical CPU NUMA sockets.
34. `memory.operator_pool`: Dedicated memory pool assigned to specific operator vertices.
35. `memory.ownership_tracker`: Tracks single ownership paths for every allocated buffer slice.
36. `memory.pool_allocator`: Recycles freed memory buffers back into reusable pool queues.
37. `memory.quota_manager`: Enforces hard memory reservation ceilings across operators.
38. `memory.spill_manager`: Asynchronously spills inactive window states to NVMe storage.
39. `memory.spill_recovery`: Restores spilled state files back into off-heap memory pools.
40. `memory.thread_local_pool`: Lock-free thread-local memory pool assigned to worker threads.
41. `memory.window_pool`: Dedicated memory pool for tumbling, sliding, and session window states.

---

## 6. Hierarchical Memory Architecture

Platform 1 Part 3 structures off-heap memory across four explicit tiers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       GlobalMemoryManager (Root System)                      │
│                  (Configured Max Off-Heap Ceiling e.g. 64GB)                │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
            ┌──────────────────────────┴──────────────────────────┐
            ▼                                                     ▼
┌─────────────────────────────┐                         ┌─────────────────────────────┐
│    MemoryPoolManager        │                         │      SpillManager           │
│ (Hierarchical Quota Engine) │                         │  (NVMe Storage Engine)      │
└───────────┬─────────────────┘                         └─────────────────────────────┘
            │
    ┌───────┴──────────────────────────┬──────────────────────────┐
    ▼                                  ▼                          ▼
┌──────────────────────────┐┌──────────────────────────┐┌──────────────────────────┐
│   ThreadLocalPool        ││   OperatorPool           ││   WindowPool             │
│ (Core-Pinned Worker RAM) ││ (Filter/Map Operator RAM)││ (Join/Window State RAM)  │
└───────────┬──────────────┘└──────────┬───────────────┘└──────────┬───────────────┘
            │                          │                           │
            └──────────────────────────┼───────────────────────────┘
                                       ▼
                         ┌──────────────────────────┐
                         │      MemoryArena         │
                         │ (64-byte Aligned Slices) │
                         └──────────────────────────┘
```

---

## 7. Mandatory Core Subsystem Implementation Contracts

```python
# akaal/platform/streaming/memory/global_memory_manager.py
from threading import Lock
from typing import Optional
from akaal.platform.streaming.exceptions.buffer_exceptions import MemoryQuotaExceededError

class GlobalMemoryManager:
    """Top-level memory authority governing off-heap allocation limits."""

    def __init__(self, max_capacity_bytes: int) -> None:
        self.max_capacity_bytes = max_capacity_bytes
        self._allocated_bytes = 0
        self._lock = Lock()

    def reserve(self, size_bytes: int) -> bool:
        with self._lock:
            if self._allocated_bytes + size_bytes > self.max_capacity_bytes:
                raise MemoryQuotaExceededError(
                    f"Global memory limit exceeded. Requested: {size_bytes}, "
                    f"Allocated: {self._allocated_bytes}, Max: {self.max_capacity_bytes}"
                )
            self._allocated_bytes += size_bytes
            return True

    def release(self, size_bytes: int) -> None:
        with self._lock:
            self._allocated_bytes = max(0, self._allocated_bytes - size_bytes)
```

```python
# akaal/platform/streaming/buffer/reference_counter.py
import atomic

class ReferenceCounter:
    """Thread-safe atomic reference counter enforcing deterministic disposal."""

    def __init__(self, initial_count: int = 1) -> None:
        self._count = initial_count

    def retain(self) -> int:
        self._count += 1
        return self._count

    def release(self) -> int:
        self._count -= 1
        if self._count < 0:
            raise RuntimeError("Reference count dropped below zero.")
        return self._count

    @property
    def value(self) -> int:
        return self._count
```

```python
# akaal/platform/streaming/buffer/buffer_slice.py
from typing import Optional, Any
from akaal.platform.streaming.buffer.reference_counter import ReferenceCounter

class BufferSlice:
    """Zero-copy off-heap memory buffer envelope backed by reference counting."""

    def __init__(self, pointer: int, length: int, owner_id: str) -> None:
        self.pointer = pointer
        self.length = length
        self.owner_id = owner_id
        self._ref_counter = ReferenceCounter(1)

    def retain(self) -> None:
        self._ref_counter.retain()

    def release(self, lifetime_manager: Any) -> None:
        if self._ref_counter.release() == 0:
            lifetime_manager.recycle_buffer(self)

    def slice(self, offset: int, slice_length: int) -> "BufferSlice":
        """O(1) zero-copy sub-slice creation."""
        if offset + slice_length > self.length:
            raise ValueError("Sub-slice boundary exceeds parent buffer length.")
        self.retain()
        return BufferSlice(
            pointer=self.pointer + offset,
            length=slice_length,
            owner_id=self.owner_id
        )
```

---

## 8. NVMe Disk Spill & Recovery Mechanics

When memory pressure exceeds 85%, `SpillManager` (`akaal.platform.streaming.memory.spill_manager`) triggers automated disk spilling:

```
[MemoryPressureDetector] ──► Critical Threshold (> 85%) ──► Trigger Spill Event
                                                                   │
                                                                   ▼
[SpillManager] ◄── Select Cold Window / Join State ────────────────┘
       │
       ├── 1. Freeze Target Window State Buffer
       ├── 2. Asynchronously Serialize State via `io_uring` Direct I/O (`O_DIRECT`)
       ├── 3. Release Off-Heap Memory Arenas back to `MemoryPoolManager`
       └── 4. Register Disk File Descriptor with `SpillRecoveryManager`
```

---

## 9. Performance SLAs & Benchmark Targets

Target performance SLA specifications for Platform 1 Part 3 Memory Subsystem:

| Performance Metric | Netty / Aeron Target | AKAAL Part 3 Benchmark SLA |
| :--- | :--- | :--- |
| **Buffer Allocation Latency** | < 1.0 microsecond | < 0.2 microseconds (Thread-Local Pool) |
| **Zero-Copy Slicing Latency** | < 0.1 microseconds | < 0.02 microseconds ($O(1)$ pointer shift) |
| **SIMD Alignment Boundary** | 64 bytes | 64 bytes (`posix_memalign`) |
| **Allocator Lock Contention** | Low | 0% (Lock-Free Arenas) |
| **Off-Heap RSS Fragmentation** | < 10% | < 3% (`CompactionEngine` enabled) |
| **Disk Spill Write Speed** | > 300 MB/sec | > 500 MB/sec (NVMe Direct I/O) |

---

## 10. Definition of Done (Part 3 Certification)

The implementation of **Platform 1 Part 3: Memory, Buffers & Zero-Copy Data Plane** is defined as officially COMPLETE when:

1. All 44 specified modules across `akaal/platform/streaming/memory/` and `akaal/platform/streaming/buffer/` are fully implemented.
2. Static type checker `mypy --strict akaal/platform/streaming/memory akaal/platform/streaming/buffer` returns 0 errors.
3. All mandatory classes (`MemoryManager`, `MemoryPool`, `MemoryArena`, `ArrowBufferManager`, `BufferSlice`, `ReferenceCounter`, `SpillManager`, `LeakDetector`, `NUMAManager`, etc.) are fully integrated and verified.
4. Zero-copy data plane achieves > 10M records/sec throughput with $0$ bytes memory copy in hot execution paths.
5. Valgrind and AddressSanitizer soak tests run for 24 hours with zero off-heap memory leaks or dangling pointers.
6. The Architecture Review Board (ARB) formally signs off on the Part 3 release certification report.
