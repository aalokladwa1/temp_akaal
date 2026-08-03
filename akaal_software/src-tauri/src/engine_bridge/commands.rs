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
    let mut bridge = state.lock().map_err(|e| e.to_string())?;
    bridge
        .invoke_capability(&capability_id, &payload)
        .map_err(|e| e.to_string())
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
