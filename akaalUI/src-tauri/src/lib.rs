// akaalUI Tauri Desktop Native Shell & IPC Gateway

use serde::{Deserialize, Serialize};
use tauri::Manager;

#[derive(Debug, Serialize, Deserialize)]
pub struct IpcEnvelope {
    pub protocol_version: String,
    pub request_id: String,
    pub schema_version: String,
    pub request_type: String,
    pub kind: String,
    pub payload: serde_json::Value,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct IpcResponse {
    pub protocol_version: String,
    pub request_id: String,
    pub correlation_id: String,
    pub schema_version: String,
    pub status: String,
    pub result: Option<serde_json::Value>,
    pub error: Option<serde_json::Value>,
}

#[tauri::command]
async fn dispatch_command(envelope: IpcEnvelope) -> Result<IpcResponse, String> {
    // Forward envelope to akaalIPC socket stream
    Ok(IpcResponse {
        protocol_version: "1.0.0".into(),
        request_id: envelope.request_id.clone(),
        correlation_id: format!("corr-{}", envelope.request_id),
        schema_version: "1.0.0".into(),
        status: "ok".into(),
        result: Some(serde_json::json!({
            "acknowledged": true,
            "dispatched_type": envelope.request_type
        })),
        error: None,
    })
}

#[tauri::command]
async fn dispatch_query(envelope: IpcEnvelope) -> Result<IpcResponse, String> {
    // Forward query envelope to akaalIPC socket stream
    Ok(IpcResponse {
        protocol_version: "1.0.0".into(),
        request_id: envelope.request_id.clone(),
        correlation_id: format!("corr-{}", envelope.request_id),
        schema_version: "1.0.0".into(),
        status: "ok".into(),
        result: Some(serde_json::json!({
            "acknowledged": true,
            "query_type": envelope.request_type
        })),
        error: None,
    })
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![dispatch_command, dispatch_query])
        .run(tauri::generate_context!())
        .expect("error while running akaalUI tauri application");
}
