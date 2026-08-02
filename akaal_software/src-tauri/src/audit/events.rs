use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub enum AuditCategory {
    Authentication,
    Session,
    Security,
    Administration,
    Migration,
    System,
}

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub enum AuditSeverity {
    Info,
    Warning,
    Error,
    Critical,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct AuditEvent {
    pub event_id: String,
    pub timestamp: String,
    pub category: AuditCategory,
    pub event_type: String,
    pub actor_username: Option<String>,
    pub severity: AuditSeverity,
    pub details: serde_json::Value,
}
