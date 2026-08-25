use crate::engine_bridge::bridge::EngineBridge;
use crate::engine_bridge::dto::{BridgeStatusDTO, CapabilityDTO, HeartbeatStatusDTO};
use std::sync::{Arc, Mutex};
use tauri::State;

pub type EngineBridgeState = Arc<Mutex<EngineBridge>>;

#[tauri::command]
pub fn get_bridge_status_cmd(
    state: State<'_, EngineBridgeState>,
) -> Result<BridgeStatusDTO, String> {
    let bridge = state.lock().map_err(|e| e.to_string())?;
    Ok(bridge.get_status())
}

#[tauri::command]
pub fn start_engine_daemon_cmd(
    state: State<'_, EngineBridgeState>,
) -> Result<BridgeStatusDTO, String> {
    let mut bridge = state.lock().map_err(|e| e.to_string())?;
    bridge.start_daemon().map_err(|e| e.to_string())?;
    Ok(bridge.get_status())
}

#[tauri::command]
pub fn stop_engine_daemon_cmd(
    state: State<'_, EngineBridgeState>,
) -> Result<BridgeStatusDTO, String> {
    let mut bridge = state.lock().map_err(|e| e.to_string())?;
    bridge.stop_daemon().map_err(|e| e.to_string())?;
    Ok(bridge.get_status())
}

#[tauri::command]
pub fn invoke_engine_capability_cmd(
    state: State<'_, EngineBridgeState>,
    capability_id: String,
    payload: String,
) -> Result<String, String> {
    let req_id = format!("req-{}", uuid::Uuid::new_v4());
    let transport = {
        let mut bridge = state.lock().map_err(|e| e.to_string())?;
        crate::engine_bridge::logging::BridgeLogger::log_request_sent(&capability_id, &req_id);

        if !bridge.registry.is_available(&capability_id) {
            let err = format!("Capability '{}' is not registered", capability_id);
            crate::engine_bridge::logging::BridgeLogger::log_response_received(&capability_id, &req_id, false);
            return Err(err);
        }

        bridge.session_manager.begin_request().map_err(|e| e.to_string())?;
        bridge.transport.clone()
    };

    // Execute IPC transport send_request outside of global state lock
    let result = transport.send_request(&capability_id, &payload);

    if let Ok(mut bridge) = state.lock() {
        bridge.session_manager.end_request();
    }

    match &result {
        Ok(_) => crate::engine_bridge::logging::BridgeLogger::log_response_received(&capability_id, &req_id, true),
        Err(_) => crate::engine_bridge::logging::BridgeLogger::log_response_received(&capability_id, &req_id, false),
    }

    result.map_err(|e| e.to_string())
}

#[tauri::command]
pub fn list_capabilities_cmd(
    state: State<'_, EngineBridgeState>,
) -> Result<Vec<CapabilityDTO>, String> {
    let bridge = state.lock().map_err(|e| e.to_string())?;
    Ok(bridge.list_capabilities())
}

#[tauri::command]
pub fn get_heartbeat_status_cmd(
    state: State<'_, EngineBridgeState>,
) -> Result<HeartbeatStatusDTO, String> {
    let bridge = state.lock().map_err(|e| e.to_string())?;
    Ok(bridge.get_heartbeat_status())
}
