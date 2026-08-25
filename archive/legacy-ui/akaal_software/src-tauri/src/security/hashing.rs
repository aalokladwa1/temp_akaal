use argon2::{
    password_hash::{PasswordHash, PasswordHasher, PasswordVerifier, SaltString},
    Argon2,
};
use zeroize::Zeroizing;

pub fn hash_password(plain_password: &str) -> Result<String, String> {
    let password_bytes = Zeroizing::new(plain_password.as_bytes().to_vec());
    let mut salt_bytes = [0u8; 16];
    salt_bytes.copy_from_slice(uuid::Uuid::new_v4().as_bytes());

    let salt = SaltString::encode_b64(&salt_bytes)
        .map_err(|e| format!("Salt generation failed: {}", e))?;
    let argon2 = Argon2::default();

    argon2
        .hash_password(&password_bytes, &salt)
        .map(|hash| hash.to_string())
        .map_err(|e| format!("Password hashing failed: {}", e))
}

pub fn verify_password(plain_password: &str, password_hash: &str) -> Result<bool, String> {
    let password_bytes = Zeroizing::new(plain_password.as_bytes().to_vec());
    let parsed_hash =
        PasswordHash::new(password_hash).map_err(|e| format!("Invalid password hash: {}", e))?;

    Ok(Argon2::default()
        .verify_password(&password_bytes, &parsed_hash)
        .is_ok())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_argon2_hashing_and_verification() {
        let password = "SecretPassword123!";
        let hash = hash_password(password).expect("Hashing should succeed");
        assert!(verify_password(password, &hash).unwrap());
        assert!(!verify_password("WrongPassword!", &hash).unwrap());
    }
}
