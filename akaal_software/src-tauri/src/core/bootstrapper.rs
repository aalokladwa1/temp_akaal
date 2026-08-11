use crate::audit::{system::create_system_event, AuditEngine, AuditSeverity};
use crate::core::config_loader::load_workspace_config;
use crate::identity::load_admin_credentials;
use crate::security::vault::load_secure_token;
use crate::session::{SessionStore, UserSession};
use serde::{Deserialize, Serialize};
use std::sync::OnceLock;

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct BootstrapStatus {
    pub is_workspace_configured: bool,
    pub is_admin_configured: bool,
    pub is_integrity_ok: bool,
    pub active_session: Option<UserSession>,
    pub last_username: Option<String>,
    pub last_display_name: Option<String>,
    pub error_message: Option<String>,
}

static CACHED_BOOTSTRAP: OnceLock<BootstrapStatus> = OnceLock::new();

pub fn execute_startup_bootstrap(app_handle: &tauri::AppHandle<tauri::Wry>) -> BootstrapStatus {
    if let Some(status) = CACHED_BOOTSTRAP.get() {
        return status.clone();
    }

    let audit = AuditEngine::global();
    audit.log_event(create_system_event(
        "STARTUP_BOOTSTRAP_BEGIN",
        None,
        AuditSeverity::Info,
        serde_json::json!({"action": "system_bootstrap_start"}),
    ));

    // 1. Load Workspace Config
    let config_res = load_workspace_config(app_handle);
    let status = match config_res {
        Err(err) => {
            audit.log_event(create_system_event(
                "BOOTSTRAP_WORKSPACE_CONFIG_ERROR",
                None,
                AuditSeverity::Warning,
                serde_json::json!({"error": &err}),
            ));
            BootstrapStatus {
                is_workspace_configured: false,
                is_admin_configured: false,
                is_integrity_ok: false,
                active_session: None,
                last_username: None,
                last_display_name: None,
                error_message: Some(err),
            }
        }
        Ok(config) => {
            if !config.onboarding_completed || config.workspace_path.trim().is_empty() {
                BootstrapStatus {
                    is_workspace_configured: false,
                    is_admin_configured: false,
                    is_integrity_ok: true,
                    active_session: None,
                    last_username: None,
                    last_display_name: None,
                    error_message: None,
                }
            } else {
                // 2. Validate Storage Path Integrity
                let target_path = std::path::Path::new(&config.workspace_path);
                if !target_path.exists() || !target_path.is_dir() {
                    audit.log_event(create_system_event(
                        "BOOTSTRAP_INTEGRITY_FAILURE",
                        None,
                        AuditSeverity::Error,
                        serde_json::json!({"workspacePath": &config.workspace_path}),
                    ));
                    BootstrapStatus {
                        is_workspace_configured: true,
                        is_admin_configured: false,
                        is_integrity_ok: false,
                        active_session: None,
                        last_username: None,
                        last_display_name: None,
                        error_message: Some(format!(
                            "Configured storage location '{}' is invalid or unaccessible.",
                            config.workspace_path
                        )),
                    }
                } else {
                    // 3. Load real administrator identity
                    let admin_opt = load_admin_credentials(app_handle).unwrap_or(None);
                    let is_admin_configured = admin_opt.is_some();
                    let (last_username, last_display_name) = admin_opt
                        .map(|a| (Some(a.username), Some(a.display_name)))
                        .unwrap_or((None, None));

                    // 4. Attempt session restoration from DPAPI vault
                    let mut restored_session: Option<UserSession> = None;
                    if let Ok(Some(token)) = load_secure_token(app_handle) {
                        if let Ok(sess) = SessionStore::global().validate_and_touch(&token) {
                            audit.log_event(create_system_event(
                                "BOOTSTRAP_SESSION_RESTORED",
                                Some(&sess.username),
                                AuditSeverity::Info,
                                serde_json::json!({"tokenId": token}),
                            ));
                            restored_session = Some(sess);
                        }
                    }

                    BootstrapStatus {
                        is_workspace_configured: true,
                        is_admin_configured,
                        is_integrity_ok: true,
                        active_session: restored_session,
                        last_username,
                        last_display_name,
                        error_message: None,
                    }
                }
            }
        }
    };

    audit.log_event(create_system_event(
        "STARTUP_BOOTSTRAP_COMPLETE",
        None,
        AuditSeverity::Info,
        serde_json::json!({
            "isWorkspaceConfigured": status.is_workspace_configured,
            "isAdminConfigured": status.is_admin_configured,
            "isIntegrityOk": status.is_integrity_ok,
            "hasActiveSession": status.active_session.is_some()
        }),
    ));

    let _ = CACHED_BOOTSTRAP.set(status.clone());
    status
}
