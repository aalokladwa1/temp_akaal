# Monitoring Module — Current Architecture & Forensic Record

**Phase Baseline:** P1.5  
**File Reference:** [`akaal_software/src/screens/MonitoringModule/MonitoringModule.tsx`](file:///a:/temp_akaal/akaal_software/src/screens/MonitoringModule/MonitoringModule.tsx)

---

## 1. Architectural Overview

The **Monitoring Module** is the canonical **Observation & Telemetry Center** of AKAAL. It is strictly decoupled from command execution and displays 6 domain tab panels:
1. **Overview Panel:** KPI summaries, health status, and domain breakdown.
2. **Performance Panel:** Rows/sec, MB/s throughput, average & peak metrics, RAM/CPU resources.
3. **Workers Panel:** Configured vs active workers, partition assignments, rows processed per worker.
4. **Tables & Partitions Panel:** Table completion list, batch sizes, latency, LOB byte totals.
5. **Reliability & Checkpoints Panel:** Checkpoint ID, last committed primary key (redacted), retry counts.
6. **Events & Logs Panel:** Event activity log stream and sanitized error tracebacks.

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
