pub mod audit;
pub mod core;
pub mod engine_bridge;
pub mod identity;
pub mod security;
pub mod session;
mod workspace_config;

use audit::{
    administration::create_administration_event, authentication::create_auth_event,
    session::create_session_event, AuditEngine, AuditSeverity,
};
use core::{execute_startup_bootstrap, BootstrapStatus};
use identity::{
    load_admin_credentials, save_admin_credentials, verify_admin_password, UserDisplayInfo,
};
use security::{
    clear_secure_token, save_secure_token, RateLimiter,
};
use serde::{Deserialize, Serialize};
use session::{generate_session_token, SessionStore, UserSession};
use workspace_config::{
    load_workspace_config_cmd, save_workspace_config_cmd, validate_workspace_path_cmd,
    WorkspaceConfig,
};

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct AuthProviderInfo {
    pub id: String,
    pub name: String,
    pub provider_type: String,
    pub supports_mfa: bool,
    pub supports_password_reset: bool,
    pub supports_remember_device: bool,
    pub supports_auto_login: bool,
    pub supports_sso: bool,
    pub supports_offline_login: bool,
    pub is_selectable: bool,
    pub status_badge: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AuthCredentials {
    pub username: String,
    pub password: ZeroizeString,
    pub remember_device: bool,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(transparent)]
pub struct ZeroizeString(pub String);

impl zeroize::Zeroize for ZeroizeString {
    fn zeroize(&mut self) {
        self.0.zeroize();
    }
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct AuthResponse {
    pub session: UserSession,
    pub message: String,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BootstrapAdminPayload {
    pub config: WorkspaceConfig,
    pub admin_full_name: String,
    pub admin_username: String,
    pub admin_password: ZeroizeString,
}

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[tauri::command]
fn exit_app(app_handle: tauri::AppHandle<tauri::Wry>) {
    app_handle.exit(0);
}

#[tauri::command]
fn bootstrap_app_cmd(app_handle: tauri::AppHandle<tauri::Wry>) -> BootstrapStatus {
    execute_startup_bootstrap(&app_handle)
}

#[tauri::command]
fn create_bootstrap_admin_cmd(
    app_handle: tauri::AppHandle<tauri::Wry>,
    payload: BootstrapAdminPayload,
) -> Result<WorkspaceConfig, String> {
    let record = save_admin_credentials(
        &app_handle,
        &payload.admin_username,
        &payload.admin_full_name,
        &payload.admin_password.0,
    )?;

    let mut config = payload.config;
    config.owner_display_name = Some(record.display_name.clone());
    config.admin_username = Some(record.username.clone());
    config.has_admin_configured = true;

    let saved_config = save_workspace_config_cmd(app_handle, config)?;

    AuditEngine::global().log_event(create_administration_event(
        "ADMIN_BOOTSTRAP_CREATED",
        Some(&record.username),
        AuditSeverity::Info,
        serde_json::json!({
            "username": record.username,
            "displayName": record.display_name,
            "role": record.role
        }),
    ));

    Ok(saved_config)
}

#[tauri::command]
fn authenticate_user_cmd(
    app_handle: tauri::AppHandle<tauri::Wry>,
    credentials: AuthCredentials,
) -> Result<AuthResponse, String> {
    let username_clean = credentials.username.trim().to_lowercase();
    let audit = AuditEngine::global();
    let rate_limiter = RateLimiter::global();

    if username_clean.is_empty() || credentials.password.0.trim().is_empty() {
        return Err("Username and password are required.".to_string());
    }

    // 1. Check Rate Limiter
    rate_limiter.check_lockout(&username_clean)?;

    // 2. Real Administrator Credential Verification against identity store
    let verified_admin = verify_admin_password(&app_handle, &username_clean, &credentials.password.0)?;

    let admin = match verified_admin {
        Some(record) => record,
        None => {
            rate_limiter.record_failure(&username_clean);
            audit.log_event(create_auth_event(
                "AUTH_FAILED_INVALID_CREDENTIALS",
                Some(&username_clean),
                AuditSeverity::Warning,
                serde_json::json!({"reason": "invalid_username_or_password"}),
            ));
            return Err("The username or password you entered is incorrect.".to_string());
        }
    };

    // Successful Login: Reset rate limiter count
    rate_limiter.reset(&username_clean);

    let session_id = generate_session_token();
    let session = SessionStore::global().create_session(
        session_id.clone(),
        format!("usr_{}", admin.username),
        admin.username.clone(),
        admin.display_name.clone(),
        admin.role,
        credentials.remember_device,
    );

    // Save to DPAPI Vault if Remember Device is selected
    if credentials.remember_device {
        let _ = save_secure_token(&app_handle, &session_id);
    } else {
        let _ = clear_secure_token(&app_handle);
    }

    audit.log_event(create_auth_event(
        "AUTH_SUCCESSFUL",
        Some(&admin.username),
        AuditSeverity::Info,
        serde_json::json!({
            "sessionId": session_id,
            "rememberDevice": credentials.remember_device
        }),
    ));

    Ok(AuthResponse {
        session,
        message: "Authentication successful.".to_string(),
    })
}

#[tauri::command]
fn validate_session_cmd(session_id: String) -> Result<UserSession, String> {
    SessionStore::global().validate_and_touch(&session_id)
}

#[tauri::command]
fn logout_session_cmd(
    app_handle: tauri::AppHandle<tauri::Wry>,
    session_id: String,
) -> Result<(), String> {
    let audit = AuditEngine::global();
    if let Some(session) = SessionStore::global().get_session(&session_id) {
        audit.log_event(create_session_event(
            "SESSION_LOGOUT",
            Some(&session.username),
            AuditSeverity::Info,
            serde_json::json!({"sessionId": session_id}),
        ));
    }

    SessionStore::global().remove_session(&session_id);
    let _ = clear_secure_token(&app_handle);
    Ok(())
}

#[tauri::command]
fn lock_session_cmd(session_id: String) -> Result<(), String> {
    SessionStore::global().lock_session(&session_id)
}

#[tauri::command]
fn unlock_session_cmd(app_handle: tauri::AppHandle<tauri::Wry>, session_id: String, password: String) -> Result<UserSession, String> {
    let session = SessionStore::global()
        .get_session(&session_id)
        .ok_or_else(|| "Session not found.".to_string())?;

    let verified = verify_admin_password(&app_handle, &session.username, &password)?;

    if verified.is_none() {
        AuditEngine::global().log_event(create_session_event(
            "SESSION_UNLOCK_FAILED",
            Some(&session.username),
            AuditSeverity::Warning,
            serde_json::json!({"sessionId": session_id}),
        ));
        return Err("Invalid password for session unlock.".to_string());
    }

    AuditEngine::global().log_event(create_session_event(
        "SESSION_UNLOCKED",
        Some(&session.username),
        AuditSeverity::Info,
        serde_json::json!({"sessionId": session_id}),
    ));

    SessionStore::global().unlock_session(&session_id)
}

#[tauri::command]
fn get_last_known_user_cmd(app_handle: tauri::AppHandle<tauri::Wry>) -> Option<UserDisplayInfo> {
    if let Ok(Some(admin)) = load_admin_credentials(&app_handle) {
        let initials = admin
            .display_name
            .split_whitespace()
            .map(|w| w.chars().next().unwrap_or(' '))
            .collect::<String>()
            .to_uppercase();

        Some(UserDisplayInfo {
            username: admin.username,
            display_name: admin.display_name,
            avatar_initials: if initials.is_empty() { "SA".to_string() } else { initials },
        })
    } else {
        None
    }
}

#[tauri::command]
fn get_auth_providers_cmd() -> Vec<AuthProviderInfo> {
    vec![
        AuthProviderInfo {
            id: "local".to_string(),
            name: "Local Account".to_string(),
            provider_type: "local".to_string(),
            supports_mfa: true,
            supports_password_reset: true,
            supports_remember_device: true,
            supports_auto_login: false,
            supports_sso: false,
            supports_offline_login: true,
            is_selectable: true,
            status_badge: None,
        },
        AuthProviderInfo {
            id: "entra_id".to_string(),
            name: "Microsoft Entra ID".to_string(),
            provider_type: "entra_id".to_string(),
            supports_mfa: true,
            supports_password_reset: false,
            supports_remember_device: true,
            supports_auto_login: true,
            supports_sso: true,
            supports_offline_login: false,
            is_selectable: false,
            status_badge: Some("Coming Soon".to_string()),
        },
        AuthProviderInfo {
            id: "active_directory".to_string(),
            name: "Active Directory / LDAP".to_string(),
            provider_type: "ldap".to_string(),
            supports_mfa: false,
            supports_password_reset: false,
            supports_remember_device: true,
            supports_auto_login: true,
            supports_sso: true,
            supports_offline_login: false,
            is_selectable: false,
            status_badge: Some("Coming Soon".to_string()),
        },
        AuthProviderInfo {
            id: "okta".to_string(),
            name: "Okta".to_string(),
            provider_type: "okta".to_string(),
            supports_mfa: true,
            supports_password_reset: false,
            supports_remember_device: true,
            supports_auto_login: true,
            supports_sso: true,
            supports_offline_login: false,
            is_selectable: false,
            status_badge: Some("Coming Soon".to_string()),
        },
        AuthProviderInfo {
            id: "google".to_string(),
            name: "Google Workspace".to_string(),
            provider_type: "google".to_string(),
            supports_mfa: true,
            supports_password_reset: false,
            supports_remember_device: true,
            supports_auto_login: true,
            supports_sso: true,
            supports_offline_login: false,
            is_selectable: false,
            status_badge: Some("Coming Soon".to_string()),
        },
        AuthProviderInfo {
            id: "oauth2".to_string(),
            name: "OAuth 2.0".to_string(),
            provider_type: "oauth2".to_string(),
            supports_mfa: true,
            supports_password_reset: false,
            supports_remember_device: true,
            supports_auto_login: false,
            supports_sso: true,
            supports_offline_login: false,
            is_selectable: false,
            status_badge: Some("Coming Soon".to_string()),
        },
        AuthProviderInfo {
            id: "saml2".to_string(),
            name: "SAML 2.0".to_string(),
            provider_type: "saml2".to_string(),
            supports_mfa: true,
            supports_password_reset: false,
            supports_remember_device: true,
            supports_auto_login: false,
            supports_sso: true,
            supports_offline_login: false,
            is_selectable: false,
            status_badge: Some("Coming Soon".to_string()),
        },
    ]
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let bridge_state: engine_bridge::commands::EngineBridgeState = std::sync::Arc::new(
        std::sync::Mutex::new(engine_bridge::EngineBridge::with_default_transport(
            engine_bridge::BridgeConfig::default(),
        )),
    );

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .manage(bridge_state)
        .invoke_handler(tauri::generate_handler![
            greet,
            exit_app,
            bootstrap_app_cmd,
            create_bootstrap_admin_cmd,
            authenticate_user_cmd,
            validate_session_cmd,
            logout_session_cmd,
            lock_session_cmd,
            unlock_session_cmd,
            get_last_known_user_cmd,
            get_auth_providers_cmd,
            load_workspace_config_cmd,
            save_workspace_config_cmd,
            validate_workspace_path_cmd,
            engine_bridge::commands::get_bridge_status_cmd,
            engine_bridge::commands::start_engine_daemon_cmd,
            engine_bridge::commands::stop_engine_daemon_cmd,
            engine_bridge::commands::invoke_engine_capability_cmd,
            engine_bridge::commands::list_capabilities_cmd,
            engine_bridge::commands::get_heartbeat_status_cmd
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
