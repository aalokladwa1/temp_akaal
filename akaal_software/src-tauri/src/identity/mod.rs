pub mod roles;

pub use roles::UserRole;
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct UserIdentity {
    pub user_id: String,
    pub username: String,
    pub display_name: String,
    pub email: String,
    pub role: UserRole,
    pub is_active: bool,
    pub created_at: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct UserDisplayInfo {
    pub username: String,
    pub display_name: String,
    pub avatar_initials: String,
}
