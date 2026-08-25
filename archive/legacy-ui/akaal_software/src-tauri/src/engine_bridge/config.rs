use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct BridgeConfig {
    pub heartbeat_interval_secs: u64,
    pub transport_timeout_secs: u64,
    pub reconnect_attempts: u32,
    pub retry_interval_secs: u64,
    pub max_concurrent_requests: u32,
    pub log_level: String,
    pub engine_executable_path: Option<String>,
    pub transport_type: String,
}

impl Default for BridgeConfig {
    fn default() -> Self {
        Self {
            heartbeat_interval_secs: 5,
            transport_timeout_secs: 30,
            reconnect_attempts: 5,
            retry_interval_secs: 2,
            max_concurrent_requests: 16,
            log_level: "INFO".to_string(),
            engine_executable_path: None,
            transport_type: "Null".to_string(),
        }
    }
}
