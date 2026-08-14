# Monitoring Module — Current Architecture & Forensic Record

**Phase Baseline:** P1.5  
**File Reference:** [`akaal_software/src/screens/MonitoringModule/MonitoringModule.tsx`](file:///a:/temp_akaal/akaal_software/src/screens/MonitoringModule/MonitoringModule.tsx)

---

## 1. Architectural Overview

The **Monitoring Module** is the canonical **Observation & Telemetry Center** of AKAAL. It is strictly decoupled from command execution.

### Information Architecture (P1.5D Landing Explorer):
```text
Monitoring (Sidebar Click)
   ↓
Monitoring Home / Migration Run Explorer (<MonitoringHome />)
   ↓ (Select Migration)
Existing Detailed Monitor (<MonitoringModule />)
   [Overview | Performance | Workers | Tables & Partitions | Reliability | Events]
```

1. **Monitoring Home Landing Experience:** Displays portfolio summary KPI cards (Total, Live, Paused, Completed, Failed, Terminated), status filters, engine pair display (`Source → Target`), search, and `LIVE` tag indicators for active runs.
2. **Overview Panel:** KPI summaries, health status, and domain breakdown.
3. **Performance Panel:** Rows/sec, MB/s throughput, average & peak metrics, RAM/CPU resources.
4. **Workers Panel:** Configured vs active workers, partition assignments, rows processed per worker.
5. **Tables & Partitions Panel:** Table completion list, batch sizes, latency, LOB byte totals.
6. **Reliability & Checkpoints Panel:** Checkpoint ID, last committed primary key (redacted), retry counts.
7. **Events & Logs Panel:** Event activity log stream and sanitized error tracebacks.

---

## 2. Live vs Historical Monitoring Semantics

| Feature / Metric | LIVE Mode (`RUNNING` / `PAUSED`) | HISTORICAL Mode (`COMPLETED` / `FAILED` / `TERMINATED`) |
| :--- | :--- | :--- |
| **Telemetry Authority** | Canonical `MetricsRegistry` + Engine Snapshots | `CentralStateStore` SQLite WAL (`artifacts/state.db`) |
| **Polling Lifecycle** | Active (2,000 ms interval) | **Paused** (Static historical run record) |
| **Live Metrics (CPU/RAM/ETA)** | Active instantaneous values | **Set to N/A / Null** (Not fabricated) |
| **Reconstructed Evidence** | Live cumulative progress | **Preserved final rows, duration, avg/peak speeds** |
| **Restart Survival** | In-memory + WAL state | **100% durable across process restarts** |

---

## 3. Boundary Contract with Mission Control

- **Mission Control = Command Center:** Responsible for launching, pausing, resuming, and terminating migrations.
- **Monitoring Module = Observation Center:** Responsible for deep telemetry inspection, worker partitioning details, WAL audit logs, and historical run reconstruction.
- **Zero Duplication:** Neither module overrides the other's canonical authority.
