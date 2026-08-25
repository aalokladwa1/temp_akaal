use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
#[serde(rename_all = "camelCase")]
pub enum BridgeStateEnum {
    Disconnected,
    Starting,
    Connected,
    Reconnecting,
    Stopping,
    Stopped,
    Error,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct BridgeStatusDTO {
    pub state: BridgeStateEnum,
    pub engine_pid: Option<u32>,
    pub active_session_id: Option<String>,
    pub transport_type: String,
    pub heartbeat_ok: bool,
    pub uptime_seconds: u64,
    pub registered_capabilities_count: usize,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct CapabilityDTO {
    pub id: String,
    pub name: String,
    pub category: String,
    pub description: String,
    pub version: String,
    pub is_available: bool,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct CapabilityResultDTO<T> {
    pub success: bool,
    pub capability_id: String,
    pub message: String,
    pub data: Option<T>,
    pub error_code: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct ProjectDTO {
    pub id: String,
    pub name: String,
    pub source_engine: String,
    pub source_endpoint: String,
    pub target_engine: String,
    pub target_endpoint: String,
    pub owner: String,
    pub created_at: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct MigrationDTO {
    pub id: String,
    pub project_id: String,
    pub name: String,
    pub source_engine: String,
    pub target_engine: String,
    pub current_stage: String,
    pub progress_pct: u8,
    pub status: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct RuntimeSessionDTO {
    pub session_id: String,
    pub migration_id: String,
    pub execution_number: u32,
    pub status: String,
    pub current_stage: String,
    pub progress_percent: u8,
    pub started_at: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct ApprovalDTO {
    pub id: String,
    pub gate: String,
    pub gate_title: String,
    pub migration_id: String,
    pub status: String,
    pub requested_by: String,
    pub summary: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct TelemetryDTO {
    pub timestamp: String,
    pub cpu_usage_pct: f32,
    pub memory_mb: u64,
    pub active_threads: u32,
    pub throughput_mbps: f32,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct DecisionDTO {
    pub id: String,
    pub timestamp: String,
    pub stage: String,
    pub subsystem: String,
    pub title: String,
    pub decision: String,
    pub reason: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct ConnectionDTO {
    pub id: String,
    pub name: String,
    pub engine: String,
    pub endpoint: String,
    pub environment: String,
    pub ssl_status: String,
    pub vault_reference: String,
    pub status: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct ValidationDTO {
    pub id: String,
    pub migration_id: String,
    pub checksum_match: bool,
    pub rows_verified: u64,
    pub discrepancies_count: u64,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct TrustCertificateDTO {
    pub id: String,
    pub migration_id: String,
    pub sha256_seal: String,
    pub certified_by: String,
    pub certified_at: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct HeartbeatStatusDTO {
    pub is_healthy: bool,
    pub last_pulse_timestamp: i64,
    pub missed_pulses: u32,
    pub latency_ms: u32,
    pub reconnect_active: bool,
}
