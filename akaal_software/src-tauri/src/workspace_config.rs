use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};
use tauri::Manager;

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct WorkspaceConfig {
    pub schema_version: u32,
    pub workspace_name: String,
    pub workspace_path: String,
    pub theme: String,
    pub onboarding_completed: bool,
    pub created_at: Option<String>,
    pub updated_at: Option<String>,
}

impl Default for WorkspaceConfig {
    fn default() -> Self {
        Self {
            schema_version: 1,
            workspace_name: "Workspace".to_string(),
            workspace_path: String::new(),
            theme: "light".to_string(),
            onboarding_completed: false,
            created_at: None,
            updated_at: None,
        }
    }
}

pub fn get_config_dir(app_handle: &tauri::AppHandle) -> Result<PathBuf, String> {
    let dir = app_handle
        .path()
        .app_config_dir()
        .map_err(|e| format!("Failed to resolve app config dir: {}", e))?;
    if !dir.exists() {
        fs::create_dir_all(&dir).map_err(|e| format!("Failed to create config dir: {}", e))?;
    }
    Ok(dir)
}

pub fn get_config_file_path(app_handle: &tauri::AppHandle) -> Result<PathBuf, String> {
    let mut path = get_config_dir(app_handle)?;
    path.push("workspace.json");
    Ok(path)
}

pub fn get_backup_file_path(app_handle: &tauri::AppHandle) -> Result<PathBuf, String> {
    let mut path = get_config_dir(app_handle)?;
    path.push("workspace.json.bak");
    Ok(path)
}

#[tauri::command]
pub fn load_workspace_config_cmd(app_handle: tauri::AppHandle) -> Result<WorkspaceConfig, String> {
    let config_path = get_config_file_path(&app_handle)?;

    if !config_path.exists() {
        return Ok(WorkspaceConfig::default());
    }

    let contents = match fs::read_to_string(&config_path) {
        Ok(c) => c,
        Err(e) => return Err(format!("Failed to read workspace.json: {}", e)),
    };

    match serde_json::from_str::<WorkspaceConfig>(&contents) {
        Ok(config) => Ok(config),
        Err(err) => {
            // Corrupted configuration recovery procedure:
            // 1. Rename workspace.json to workspace.json.bak
            let backup_path = get_backup_file_path(&app_handle)?;
            let _ = fs::rename(&config_path, &backup_path);
            
            eprintln!(
                "Corrupted workspace.json detected ({}). Renamed to workspace.json.bak",
                err
            );
            
            // 2. Return fresh default configuration to restart onboarding safely
            Ok(WorkspaceConfig::default())
        }
    }
}

#[tauri::command]
pub fn save_workspace_config_cmd(
    app_handle: tauri::AppHandle,
    mut config: WorkspaceConfig,
) -> Result<WorkspaceConfig, String> {
    // 1. Validate inputs
    let trimmed_name = config.workspace_name.trim();
    if trimmed_name.is_empty() || trimmed_name.len() > 100 {
        return Err("Workspace name must be between 1 and 100 characters.".to_string());
    }
    config.workspace_name = trimmed_name.to_string();

    let target_dir = Path::new(&config.workspace_path);
    if config.workspace_path.trim().is_empty() {
        return Err("Workspace path cannot be empty.".to_string());
    }

    // 2. Create target workspace directory tree
    if !target_dir.exists() {
        fs::create_dir_all(target_dir)
            .map_err(|e| format!("Failed to create workspace directory: {}", e))?;
    }

    // Create required subdirectories
    let subdirs = ["projects", "reports", "logs", "temp", "settings"];
    for sub in &subdirs {
        let sub_path = target_dir.join(sub);
        if !sub_path.exists() {
            fs::create_dir_all(&sub_path)
                .map_err(|e| format!("Failed to create subdirectory {}: {}", sub, e))?;
        }
    }

    // Mark onboarding as complete and update timestamps
    config.onboarding_completed = true;
    let now = chrono_timestamp();
    if config.created_at.is_none() {
        config.created_at = Some(now.clone());
    }
    config.updated_at = Some(now);

    // 3. Write workspace.json atomically (workspace.json.tmp -> workspace.json)
    let config_path = get_config_file_path(&app_handle)?;
    let tmp_path = config_path.with_extension("json.tmp");

    let json_bytes = serde_json::to_string_pretty(&config)
        .map_err(|e| format!("Failed to serialize workspace config: {}", e))?;

    fs::write(&tmp_path, json_bytes)
        .map_err(|e| format!("Failed to write temporary config: {}", e))?;

    fs::rename(&tmp_path, &config_path)
        .map_err(|e| format!("Failed to atomically rename workspace config: {}", e))?;

    // 4. Read workspace.json back and verify persisted values match memory
    let read_back_contents = fs::read_to_string(&config_path)
        .map_err(|e| format!("Failed to read back persisted workspace.json: {}", e))?;

    let verified_config: WorkspaceConfig = serde_json::from_str(&read_back_contents)
        .map_err(|e| format!("Failed to deserialize verified workspace.json: {}", e))?;

    if verified_config.workspace_name != config.workspace_name
        || verified_config.workspace_path != config.workspace_path
        || verified_config.theme != config.theme
        || !verified_config.onboarding_completed
    {
        return Err("Persistence verification failed: Persisted values do not match memory config.".to_string());
    }

    // 5. Return verified configuration
    Ok(verified_config)
}

#[tauri::command]
pub fn validate_workspace_path_cmd(path: String) -> Result<bool, String> {
    let trimmed = path.trim();
    if trimmed.is_empty() {
        return Ok(false);
    }
    let p = Path::new(trimmed);
    if p.exists() {
        if !p.is_dir() {
            return Err("Target path exists but is not a directory.".to_string());
        }
        if let Ok(md) = fs::metadata(p) {
            if md.permissions().readonly() {
                return Err("Target directory is read-only.".to_string());
            }
        }
        return Ok(true);
    }

    let mut current = p;
    while let Some(parent) = current.parent() {
        if parent.as_os_str().is_empty() {
            break;
        }
        if parent.exists() {
            if !parent.is_dir() {
                return Err("Parent directory is not a valid directory.".to_string());
            }
            if let Ok(md) = fs::metadata(parent) {
                if md.permissions().readonly() {
                    return Err("Parent directory is read-only.".to_string());
                }
            }
            return Ok(true);
        }
        current = parent;
    }
    Ok(true)
}

fn chrono_timestamp() -> String {
    // Simple ISO 8601 string representation
    format!("{:?}", std::time::SystemTime::now())
}
