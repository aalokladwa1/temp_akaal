use super::events::{AuditCategory, AuditEvent, AuditSeverity};
use uuid::Uuid;

pub fn create_session_event(
    event_type: &str,
    username: Option<&str>,
    severity: AuditSeverity,
    details: serde_json::Value,
) -> AuditEvent {
    AuditEvent {
        event_id: Uuid::new_v4().to_string(),
        timestamp: chrono::Utc::now().to_rfc3339(),
        category: AuditCategory::Session,
        event_type: event_type.to_string(),
        actor_username: username.map(|s| s.to_string()),
        severity,
        details,
    }
}
