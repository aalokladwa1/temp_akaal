use uuid::Uuid;

pub fn generate_session_token() -> String {
    let raw_uuid = Uuid::new_v4();
    format!("sess_{}", raw_uuid.simple())
}
