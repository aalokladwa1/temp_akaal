# Accumulated Requirements for Future Migration Module Redesign

**Phase Baseline:** P1.5
**Redesign Execution:** Scheduled post-P7

---

## 1. Unified Operational Canvas

When the Migration Module undergoes redesign post-P7, the new design will combine Mission Control execution and Monitoring observation into a single unified operational workspace while preserving strict backend decoupling:
1. **Dynamic Stage Progress Timeline:** Full 20-stage interactive progress track (`WF-001` through `WF-020`).
2. **Integrated Cutover & Gate Status Bar:** Explicit indicators for `GATE 1`, `GATE 2`, `GATE 3` multi-custody approvals.
3. **Multi-Database Topology Visualizer:** Graph display of source database engine, active partition streams, and target database tables.
4. **CDC Stream Gauge:** Real-time LogMiner / WAL replication lag gauges (ms) and event throughput rate.

---

## 2. Redesign Invariants

- **Desktop-First Tauri App:** React + TypeScript.
- **Enterprise Design System:** Light Theme (`.app-theme-light`) & Dark Theme (`.app-theme-dark`).
- **Zero Frontend Fakes:** 100% backend-driven runtime telemetry via `EngineGateway`.
