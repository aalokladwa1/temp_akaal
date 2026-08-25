use chrono::Utc;
use serde::Serialize;

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct BridgeLogEvent {
    pub timestamp: String,
    pub event_type: String,
    pub capability: Option<String>,
    pub request_id: Option<String>,
    pub message: String,
    pub success: bool,
}

pub struct BridgeLogger;

impl BridgeLogger {
    pub fn log(event_type: &str, capability: Option<&str>, request_id: Option<&str>, message: &str, success: bool) {
        let entry = BridgeLogEvent {
            timestamp: Utc::now().to_rfc3339(),
            event_type: event_type.to_string(),
            capability: capability.map(|s| s.to_string()),
            request_id: request_id.map(|s| s.to_string()),
            message: message.to_string(),
            success,
        };

        if let Ok(json) = serde_json::to_string(&entry) {
            println!("[AKAAL ENGINE BRIDGE] {}", json);
        }
    }

    pub fn log_request_sent(capability: &str, req_id: &str) {
        Self::log("RequestSent", Some(capability), Some(req_id), &format!("Dispatching capability request '{}'", capability), true);
    }

    pub fn log_response_received(capability: &str, req_id: &str, success: bool) {
        Self::log("ResponseReceived", Some(capability), Some(req_id), &format!("Response received for '{}'", capability), success);
    }

    pub fn log_heartbeat(missed: u32, healthy: bool) {
        Self::log("HeartbeatPulse", None, None, &format!("Heartbeat status checked (Missed: {}, Healthy: {})", missed, healthy), healthy);
    }

    pub fn log_connection_change(old_state: &str, new_state: &str) {
        Self::log("ConnectionStateChange", None, None, &format!("Bridge state changed from {} -> {}", old_state, new_state), true);
    }
}
