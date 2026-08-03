use serde::{Deserialize, Serialize};
use std::fmt;

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
#[serde(tag = "type", content = "message")]
pub enum BridgeError {
    EngineUnavailable(String),
    EngineNotRunning(String),
    CapabilityUnavailable(String),
    TransportFailure(String),
    Timeout(String),
    HeartbeatLost(String),
    InvalidPayload(String),
    SerializationFailure(String),
    PermissionDenied(String),
    Cancelled(String),
    NotYetImplemented(String),
}

impl fmt::Display for BridgeError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            BridgeError::EngineUnavailable(msg) => write!(f, "Engine Unavailable: {}", msg),
            BridgeError::EngineNotRunning(msg) => write!(f, "Engine Not Running: {}", msg),
            BridgeError::CapabilityUnavailable(msg) => write!(f, "Capability Unavailable: {}", msg),
            BridgeError::TransportFailure(msg) => write!(f, "Transport Failure: {}", msg),
            BridgeError::Timeout(msg) => write!(f, "Transport Timeout: {}", msg),
            BridgeError::HeartbeatLost(msg) => write!(f, "Heartbeat Lost: {}", msg),
            BridgeError::InvalidPayload(msg) => write!(f, "Invalid Payload: {}", msg),
            BridgeError::SerializationFailure(msg) => write!(f, "Serialization Failure: {}", msg),
            BridgeError::PermissionDenied(msg) => write!(f, "Permission Denied: {}", msg),
            BridgeError::Cancelled(msg) => write!(f, "Operation Cancelled: {}", msg),
            BridgeError::NotYetImplemented(msg) => write!(f, "Not Yet Implemented: {}", msg),
        }
    }
}

impl std::error::Error for BridgeError {}
