use crate::workspace_config::{get_config_file_path, WorkspaceConfig};
use std::fs;

pub fn load_workspace_config(app_handle: &tauri::AppHandle<tauri::Wry>) -> Result<WorkspaceConfig, String> {
    let config_path = get_config_file_path(app_handle)?;
    if !config_path.exists() {
        return Ok(WorkspaceConfig::default());
    }

    let contents = fs::read_to_string(&config_path)
        .map_err(|e| format!("Failed to read workspace config: {}", e))?;

    serde_json::from_str::<WorkspaceConfig>(&contents)
        .map_err(|e| format!("Failed to parse workspace config: {}", e))
}
