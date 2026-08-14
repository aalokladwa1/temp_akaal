# Mission Control — Current Architecture & Forensic Audit Record

**Phase Baseline:** P1.5  
**File Reference:** [`akaal_software/src/screens/MigrationModule/MissionControlView.tsx`](file:///a:/temp_akaal/akaal_software/src/screens/MigrationModule/MissionControlView.tsx)

---

## 1. Architectural Overview

Mission Control serves as the **Execution and Command Center** for AKAAL database migrations. It provides:
- Live status banner and lifecycle controls (Start, Pause, Resume, Terminate).
- Stage progression pipeline (`schema_exec`, `transport`, `validation`, `certification`, `completed`).
- Operational KPI summary (rows transferred, throughput MB/s, ETA, active workers, queue depth).
- Live activity and event log stream.
- Mission Replay™ inspection.

---

## 2. Complete Call Graph

```text
MissionControlView.tsx (Operator presses Start Migration)
   ↓ executeConfirmedAction('start')
ipcService.invokeEngineCapability('start_transport', { migration_id: migId })
   ↓ Tauri IPC Invoke
commands.rs (invoke_engine_capability_cmd)
   ↓ Named Pipe / Unix Domain Socket
ipc_server.py (handle_capability_request)
   ↓ engine_gateway.invoke('start_transport', payload)
EngineGateway.start_transport(payload)
   ↓ Pre-flight contract validation & atomic_claim_start()
   ↓ ThreadPool Handoff (_bg_execute)
AkaalSuperEngine.execute_migration(workflow_id, spec_dict, dag_dict, source_params, target_params, is_physical=True)
   ↓ Physical Execution Path
PreStartValidationStep.execute(wf_ctx)
   ↓
SchemaExecutionStep.execute(wf_ctx)
   ↓
DataTransportStep.execute(wf_ctx)
   ↓
ParallelReplicationScheduler & Physical Readers/Writers (OraclePhysicalReader → PostgreSQLPhysicalWriter)
   ↓
Real Target Database Tables
```

---

## 3. Start Migration Verification Truth

| Verification Claim | Status | Factual Basis |
| :--- | :---: | :--- |
| **`MISSION_CONTROL_START_BUTTON_REAL`** | **YES** | Triggers `executeConfirmedAction('start')` in `MissionControlView.tsx`. |
| **`START_BUTTON_REACHES_ENGINE_GATEWAY`** | **YES** | Invokes IPC capability `start_transport` which lands in `EngineGateway.start_transport()`. |
| **`START_BUTTON_REACHES_SUPER_ENGINE`** | **YES** | `EngineGateway` hands off to `AkaalSuperEngine.execute_migration()`. |
| **`START_BUTTON_REACHES_WORKFLOW_ENGINE`** | **YES** | `AkaalSuperEngine` delegates to `WorkflowEngine` step execution. |
| **`START_BUTTON_REACHES_DATA_TRANSPORT`** | **YES** | `DataTransportStep.execute()` is invoked for physical batch streaming. |
| **`START_BUTTON_CAN_REACH_REAL_DATABASES`** | **YES** | Connects `OraclePhysicalReader` to `PostgreSQLPhysicalWriter` for physical SQL execution. |

---

## 4. Operator Control Verification Truth

- **`MISSION_CONTROL_PAUSE_REAL = YES`**: Invokes `pause_migration` capability, calling `state_store.update_progress` with status `PAUSED` and setting cancellation signals.
- **`MISSION_CONTROL_RESUME_REAL = YES`**: Invokes `resume_migration` capability, restoring `RUNNING` status and worker polling.
- **`MISSION_CONTROL_TERMINATE_REAL = YES`**: Invokes `terminate_migration` capability, setting status to `TERMINATED`, halting worker background threads, and persisting terminal status to SQLite WAL.

---

## 5. Technical Debt & Future Redesign Requirements

1. **Information Density & Hierarchy:** KPI cards and progress bars will require higher density when P2–P6 introduce multi-table DAGs, CDC stream metrics, and Merkle tree checksum trees.
2. **CDC Stream Representation:** Future P4 requires continuous change data capture lag counters (ms) and LSN transaction stream indicators.
3. **Cutover & Hypercare Controls:** Future P7 requires explicit production cutover gating controls, traffic flip buttons, and hypercare health gauges.
