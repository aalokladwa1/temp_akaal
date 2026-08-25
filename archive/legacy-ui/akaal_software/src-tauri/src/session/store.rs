use crate::identity::UserRole;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Mutex, OnceLock};

const INACTIVITY_LOCK_SECS: i64 = 900; // 15 minutes
const MAX_SESSION_TTL_SECS: i64 = 86400; // 24 hours

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct UserSession {
    pub session_id: String,
    pub user_id: String,
    pub username: String,
    pub display_name: String,
    pub role: UserRole,
    pub created_at: i64,
    pub last_accessed_at: i64,
    pub expires_at: i64,
    pub is_locked: bool,
    pub remember_device: bool,
}

pub struct SessionStore {
    sessions: Mutex<HashMap<String, UserSession>>,
}

impl SessionStore {
    pub fn global() -> &'static SessionStore {
        static INSTANCE: OnceLock<SessionStore> = OnceLock::new();
        INSTANCE.get_or_init(|| SessionStore {
            sessions: Mutex::new(HashMap::new()),
        })
    }

    pub fn create_session(
        &self,
        session_id: String,
        user_id: String,
        username: String,
        display_name: String,
        role: UserRole,
        remember_device: bool,
    ) -> UserSession {
        let now = chrono::Utc::now().timestamp();
        let session = UserSession {
            session_id: session_id.clone(),
            user_id,
            username,
            display_name,
            role,
            created_at: now,
            last_accessed_at: now,
            expires_at: now + MAX_SESSION_TTL_SECS,
            is_locked: false,
            remember_device,
        };

        if let Ok(mut guard) = self.sessions.lock() {
            guard.insert(session_id, session.clone());
        }

        session
    }

    pub fn validate_and_touch(&self, session_id: &str) -> Result<UserSession, String> {
        let now = chrono::Utc::now().timestamp();
        if let Ok(mut guard) = self.sessions.lock() {
            if let Some(session) = guard.get_mut(session_id) {
                // Check 24-hr TTL Expiration
                if now > session.expires_at {
                    return Err("Session has expired (24h TTL limit reached).".to_string());
                }

                // Check Inactivity Lock
                if !session.is_locked && (now - session.last_accessed_at > INACTIVITY_LOCK_SECS) {
                    session.is_locked = true;
                }

                if session.is_locked {
                    return Err("Session is locked due to inactivity.".to_string());
                }

                session.last_accessed_at = now;
                return Ok(session.clone());
            }
        }
        Err("Session not found or invalid.".to_string())
    }

    pub fn get_session(&self, session_id: &str) -> Option<UserSession> {
        if let Ok(guard) = self.sessions.lock() {
            return guard.get(session_id).cloned();
        }
        None
    }

    pub fn lock_session(&self, session_id: &str) -> Result<(), String> {
        if let Ok(mut guard) = self.sessions.lock() {
            if let Some(session) = guard.get_mut(session_id) {
                session.is_locked = true;
                return Ok(());
            }
        }
        Err("Session not found.".to_string())
    }

    pub fn unlock_session(&self, session_id: &str) -> Result<UserSession, String> {
        let now = chrono::Utc::now().timestamp();
        if let Ok(mut guard) = self.sessions.lock() {
            if let Some(session) = guard.get_mut(session_id) {
                session.is_locked = false;
                session.last_accessed_at = now;
                return Ok(session.clone());
            }
        }
        Err("Session not found.".to_string())
    }

    pub fn remove_session(&self, session_id: &str) {
        if let Ok(mut guard) = self.sessions.lock() {
            guard.remove(session_id);
        }
    }
}
