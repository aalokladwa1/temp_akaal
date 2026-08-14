# Production-Reachable Backend Capabilities Inventory

**Phase Baseline:** P1.5  

---

## 1. EngineGateway Capabilities Registered & Reachable

| Capability ID | Category | Implementation Owner | Production Status |
| :--- | :--- | :--- | :---: |
| `get_engine_status` | System | `EngineGateway.get_engine_status()` | **PRODUCTION_REACHABLE** |
| `test_connection` | Connectivity | `EngineGateway.test_connection()` | **PRODUCTION_REACHABLE** |
| `create_project` | Project | `CentralStateStore` | **PRODUCTION_REACHABLE** |
| `create_migration` | Pipeline | `CentralStateStore` | **PRODUCTION_REACHABLE** |
| `run_preflight` | Execution | `DiscoveryOrchestrator` & `AdvisorEngine` | **PRODUCTION_REACHABLE** |
| `generate_plan` | Execution | `PlanningPipeline` & `PlannerPlatform` | **PRODUCTION_REACHABLE** |
| `request_approval` | Governance | `PolicyEngine` | **PRODUCTION_REACHABLE** |
| `submit_approval_decision` | Governance | `PolicyEngine` | **PRODUCTION_REACHABLE** |
| `execute_schema` | Execution | `SchemaEvolutionPlatformV5` | **PRODUCTION_REACHABLE** |
| `start_transport` | Execution | `AkaalSuperEngine` & `DataTransportStep` | **PRODUCTION_REACHABLE** |
| `pause_migration` | Execution | `EngineGateway.pause_migration()` | **PRODUCTION_REACHABLE** |
| `resume_migration` | Execution | `EngineGateway.resume_migration()` | **PRODUCTION_REACHABLE** |
| `terminate_migration` | Execution | `EngineGateway.terminate_migration()` | **PRODUCTION_REACHABLE** |
| `rollback_migration` | Recovery | `EngineGateway.rollback_migration()` | **PRODUCTION_REACHABLE** |
| `run_validation` | Verification | `ValidationStep` | **PRODUCTION_REACHABLE** |
| `generate_certificate` | Certification | `DigitalCertificationSealer` | **PRODUCTION_REACHABLE** |
| `get_runtime_snapshot` | Runtime | `EngineGateway.get_runtime_snapshot()` | **PRODUCTION_REACHABLE** |
| `get_monitoring_snapshot` | Runtime | `EngineGateway.get_monitoring_snapshot()` | **PRODUCTION_REACHABLE** |
