use crate::identity::UserRole;
use crate::security::hashing::{hash_password, verify_password};
use crate::workspace_config::get_config_dir;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct AdminCredentialRecord {
    pub username: String,
    pub display_name: String,
    pub password_hash: String,
    pub role: UserRole,
    pub created_at: String,
}

pub fn get_identity_file_path(app_handle: &tauri::AppHandle<tauri::Wry>) -> Result<PathBuf, String> {
    let mut path = get_config_dir(app_handle)?;
    path.push("identity.json");
    Ok(path)
}

pub fn save_admin_credentials(
    app_handle: &tauri::AppHandle<tauri::Wry>,
    username: &str,
    display_name: &str,
    plain_password: &str,
) -> Result<AdminCredentialRecord, String> {
    let clean_username = username.trim().to_lowercase();
    let clean_display_name = display_name.trim().to_string();

    if clean_username.len() < 3 {
        return Err("Username must be at least 3 characters.".to_string());
    }
    if clean_display_name.len() < 2 {
        return Err("Full name must be at least 2 characters.".to_string());
    }
    if plain_password.len() < 8 {
        return Err("Password must be at least 8 characters.".to_string());
    }

    let password_hash = hash_password(plain_password)?;

    let record = AdminCredentialRecord {
        username: clean_username,
        display_name: clean_display_name,
        password_hash,
        role: UserRole::SuperAdministrator,
        created_at: chrono::Utc::now().to_rfc3339(),
    };

    let path = get_identity_file_path(app_handle)?;
    let json_bytes = serde_json::to_string_pretty(&record)
        .map_err(|e| format!("Failed to serialize identity record: {}", e))?;

    fs::write(&path, json_bytes)
        .map_err(|e| format!("Failed to save administrator identity: {}", e))?;

    Ok(record)
}

pub fn load_admin_credentials(
    app_handle: &tauri::AppHandle<tauri::Wry>,
) -> Result<Option<AdminCredentialRecord>, String> {
    let path = get_identity_file_path(app_handle)?;
    if !path.exists() {
        return Ok(None);
    }

    let contents = fs::read_to_string(&path)
        .map_err(|e| format!("Failed to read identity record: {}", e))?;

    let record = serde_json::from_str::<AdminCredentialRecord>(&contents)
        .map_err(|e| format!("Failed to parse identity record: {}", e))?;

    Ok(Some(record))
}

pub fn verify_admin_password(
    app_handle: &tauri::AppHandle<tauri::Wry>,
    username: &str,
    plain_password: &str,
) -> Result<Option<AdminCredentialRecord>, String> {
    let clean_username = username.trim().to_lowercase();
    let record_opt = load_admin_credentials(app_handle)?;

    if let Some(record) = record_opt {
        if record.username == clean_username {
            let is_valid = verify_password(plain_password, &record.password_hash)?;
            if is_valid {
                return Ok(Some(record));
            }
        }
    }
    Ok(None)
}
