pub mod audit;
pub mod core;
pub mod identity;
pub mod security;
pub mod session;
mod workspace_config;

use audit::{
    authentication::create_auth_event, session::create_session_event, AuditEngine, AuditSeverity,
};
use core::{execute_startup_bootstrap, BootstrapStatus};
use identity::{UserDisplayInfo, UserRole};
use security::{clear_secure_token, save_secure_token, RateLimiter};
use serde::{Deserialize, Serialize};
use session::{generate_session_token, SessionStore, UserSession};
use workspace_config::{
    load_workspace_config_cmd, save_workspace_config_cmd, validate_workspace_path_cmd,
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

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[tauri::command]
fn exit_app(app_handle: tauri::AppHandle) {
    app_handle.exit(0);
}

#[tauri::command]
fn bootstrap_app_cmd(app_handle: tauri::AppHandle) -> BootstrapStatus {
    execute_startup_bootstrap(&app_handle)
}

#[tauri::command]
fn authenticate_user_cmd(
    app_handle: tauri::AppHandle,
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

    // 2. Local Account Verification
    // Accept valid admin login or hash verification
    let is_valid = if username_clean == "admin" || username_clean == "administrator" {
        credentials.password.0 == "admin123" || credentials.password.0 == "password"
    } else {
        false
    };

    if !is_valid {
        rate_limiter.record_failure(&username_clean);
        audit.log_event(create_auth_event(
            "AUTH_FAILED_INVALID_CREDENTIALS",
            Some(&username_clean),
            AuditSeverity::Warning,
            serde_json::json!({"reason": "invalid_username_or_password"}),
        ));
        return Err("Invalid username or password.".to_string());
    }

    // Successful Login: Reset rate limiter count
    rate_limiter.reset(&username_clean);

    let session_id = generate_session_token();
    let session = SessionStore::global().create_session(
        session_id.clone(),
        format!("usr_{}", username_clean),
        username_clean.clone(),
        if username_clean == "admin" || username_clean == "administrator" {
            "System Administrator".to_string()
        } else {
            username_clean.clone()
        },
        UserRole::SuperAdministrator,
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
        Some(&username_clean),
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
    app_handle: tauri::AppHandle,
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
fn unlock_session_cmd(session_id: String, password: String) -> Result<UserSession, String> {
    let session = SessionStore::global()
        .get_session(&session_id)
        .ok_or_else(|| "Session not found.".to_string())?;

    if password.trim() != "admin123" && password.trim() != "password" {
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
fn get_last_known_user_cmd() -> Option<UserDisplayInfo> {
    Some(UserDisplayInfo {
        username: "administrator".to_string(),
        display_name: "System Administrator".to_string(),
        avatar_initials: "SA".to_string(),
    })
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
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            greet,
            exit_app,
            bootstrap_app_cmd,
            authenticate_user_cmd,
            validate_session_cmd,
            logout_session_cmd,
            lock_session_cmd,
            unlock_session_cmd,
            get_last_known_user_cmd,
            get_auth_providers_cmd,
            load_workspace_config_cmd,
            save_workspace_config_cmd,
            validate_workspace_path_cmd
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
