use crate::engine_bridge::dto::CapabilityDTO;
use std::collections::HashMap;

pub struct CapabilityRegistry {
    capabilities: HashMap<String, CapabilityDTO>,
}

impl CapabilityRegistry {
    pub fn new() -> Self {
        let mut registry = Self {
            capabilities: HashMap::new(),
        };
        registry.register_default_capabilities();
        registry
    }

    fn register_default_capabilities(&mut self) {
        let default_list = vec![
            ("get_engine_status", "Get Engine Status", "System", "Query engine daemon health, thread pool, and uptime"),
            ("supported_engines", "Supported Engines", "Metadata", "Query supported enterprise source and target engines"),
            ("create_project", "Create Project", "Project", "Initialize project workspace container"),
            ("create_migration", "Create Migration", "Pipeline", "Register migration pipeline definition"),
            ("move_migration_to_project", "Move Migration to Project", "Pipeline", "Reparent migration pipeline definition"),
            ("test_connection", "Test Connection", "Connectivity", "Validate connectivity & SSL handshake with target database"),
            ("run_preflight", "Run Preflight Check", "Execution", "Execute source discovery catalog profiling, advisor risk analysis, & planning"),
            ("start_preflight", "Start Preflight Async Operation", "Execution", "Launch asynchronous source discovery and preflight profiling task"),
            ("get_preflight_operation", "Get Preflight Operation Status", "Execution", "Query live progress and result of preflight operation"),
            ("get_migration_result", "Get Migration Final Result", "Pipeline", "Query post-migration audit result and reconciliation statistics"),
            ("start_scout", "Start Scout Discovery", "Execution", "Phase 1: Execute Scout schema discovery & lock analysis"),
            ("run_advisor", "Run Advisor Analysis", "Execution", "Phase 2: Perform compatibility, risk & constraint matrix evaluation"),
            ("generate_plan", "Generate Migration Plan", "Execution", "Phase 4: Build topological batch graph & concurrency strategy"),
            ("request_approval", "Request Governance Approval", "Governance", "Phase 5: Submit Four-Eyes multi-custody approval request"),
            ("get_approval_queue", "Get Approval Queue", "Governance", "Query active governance approval queue and pending items"),
            ("get_approvals", "Get Approvals List", "Governance", "Query governance approval history and decisions"),
            ("submit_approval_decision", "Submit Approval Decision", "Governance", "Submit decision (approved/rejected) for governance gate"),
            ("process_approval", "Process Approval Gate", "Governance", "Process gate authorization decision"),
            ("execute_schema", "Execute Target Schema", "Execution", "Phase 2: Generate & apply target DDL, indexes, and constraints"),
            ("start_transport", "Start Data Transport", "Execution", "Phase 3: Launch high-throughput parallel stream partitioners"),
            ("pause_transport", "Pause Data Transport", "Execution", "Phase 3: Gracefully halt active streaming partitions"),
            ("pause_migration", "Pause Migration", "Execution", "Gracefully pause active migration pipeline execution"),
            ("resume_migration", "Resume Migration", "Execution", "Resume paused migration pipeline execution"),
            ("resume_transport", "Resume Transport", "Execution", "Resume active streaming data transport"),
            ("trigger_checkpoint", "Trigger Checkpoint", "Execution", "Persist LSN snapshot and execution checkpoint"),
            ("create_checkpoint", "Create Checkpoint", "Execution", "Flush buffer and record execution checkpoint"),
            ("rollback_migration", "Rollback Migration", "Recovery", "Revert target schema and execution state to clean checkpoint"),
            ("terminate_migration", "Terminate Migration", "Execution", "Cancel and clean up active migration pipeline"),
            ("run_validation", "Run Validation", "Verification", "Phase 4: Perform column-level checksum & referential integrity audit"),
            ("execute_healing", "Execute Self-Healing", "Recovery", "Phase 5: Trigger healer decision matrix for FK/type conflicts"),
            ("get_runtime_snapshot", "Get Runtime Snapshot", "Runtime", "Query live execution state, telemetry, and active worker statuses"),
            ("get_monitoring_snapshot", "Get Monitoring Snapshot", "Runtime", "Query canonical monitoring snapshot DTO"),
            ("get_all_migrations", "Get All Migrations", "Pipeline", "Query all registered and historical migration jobs"),
            ("subscribe_runtime_events", "Subscribe Runtime Events", "Runtime", "Subscribe to real-time engine event stream channel"),
        ];

        for (id, name, cat, desc) in default_list {
            self.capabilities.insert(
                id.to_string(),
                CapabilityDTO {
                    id: id.to_string(),
                    name: name.to_string(),
                    category: cat.to_string(),
                    description: desc.to_string(),
                    version: "1.0.0".to_string(),
                    is_available: true,
                },
            );
        }
    }

    pub fn is_available(&self, capability_id: &str) -> bool {
        self.capabilities
            .get(capability_id)
            .map(|c| c.is_available)
            .unwrap_or(false)
    }

    pub fn get_capability(&self, capability_id: &str) -> Option<&CapabilityDTO> {
        self.capabilities.get(capability_id)
    }

    pub fn list_all(&self) -> Vec<CapabilityDTO> {
        let mut list: Vec<CapabilityDTO> = self.capabilities.values().cloned().collect();
        list.sort_by(|a, b| a.id.cmp(&b.id));
        list
    }

    pub fn count(&self) -> usize {
        self.capabilities.len()
    }
}

impl Default for CapabilityRegistry {
    fn default() -> Self {
        Self::new()
    }
}
