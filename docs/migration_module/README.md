# AKAAL Migration Module Evolution Record

**Document Version:** 1.0.0
**Status:** Canonical Evolution Record
**Purpose:** Single authoritative repository documenting the capabilities, architectural boundaries, technical debt, and future redesign requirements of the AKAAL Migration Module across phases P0 through P7.

---

## Why This Directory Exists

The **AKAAL Migration Module** encompasses both operator-facing command centers (**Mission Control**) and observation/telemetry centers (**Monitoring**).

To prevent premature visual redesigns while core platform capabilities accumulate during phases P2–P7, **visual architecture is frozen**.

This directory serves as the durable record where:
1. Current architecture and backend consumption are factually documented.
2. Every capability added in future phases (P2–P7) is formally recorded.
3. Accumulated UX requirements and technical debt are systematically collected.
4. The eventual unified Migration Module redesign (scheduled post-P7) is prepared with complete architectural clarity.

---

## Governance Rules & Constraints

1. **NO PREMATURE REDESIGN:** Do not perform visual or structural UI redesigns of Mission Control during phases P1–P6.
2. **FREEZE VISUALS, NOT CORRECTNESS:** Correctness, security, and data integrity defects must be fixed surgically without changing visual layout contracts.
3. **MISSION CONTROL = EXECUTION / COMMAND CENTER:** Responsible for workflow triggers, lifecycle control (Start, Pause, Resume, Terminate), and operational governance.
4. **MONITORING = OBSERVATION / TELEMETRY CENTER:** Responsible for live metrics, worker breakdown, table progress, WAL checkpoints, and restart-safe historical run evidence.
5. **FAIL-CLOSED GOVERNANCE:** Zero frontend-authoritative state transitions; 100% driven by backend `EngineGateway` and `CentralStateStore`.

---

## Directory Structure

```text
docs/migration_module/
├── README.md
├── current_state/
│   ├── mission_control.md
│   ├── monitoring.md
│   └── workflows.md
├── capability_evolution/
│   ├── P0.md
│   ├── P1.md
│   ├── P2.md
│   ├── P3.md
│   ├── P4.md
│   ├── P5.md
│   ├── P6.md
│   └── P7.md
├── redesign_requirements/
│   ├── accumulated_requirements.md
│   ├── known_ui_debt.md
│   └── redesign_constraints.md
└── evidence/
    ├── runtime_capabilities.md
    └── database_support_matrix.md
```
