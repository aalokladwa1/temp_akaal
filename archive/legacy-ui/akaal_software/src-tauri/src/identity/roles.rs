use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub enum UserRole {
    SuperAdministrator,
    Administrator,
    MigrationEngineer,
    Auditor,
    ReadOnly,
    SupportEngineer,
}

impl Default for UserRole {
    fn default() -> Self {
        UserRole::SuperAdministrator
    }
}
