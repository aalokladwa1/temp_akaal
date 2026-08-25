pub trait BiometricAuthProvider {
    fn is_available(&self) -> bool;
    fn authenticate_biometric(&self, prompt_message: &str) -> Result<bool, String>;
}

pub trait HardwareTokenProvider {
    fn is_token_inserted(&self) -> bool;
    fn verify_hardware_signature(&self, challenge: &[u8]) -> Result<Vec<u8>, String>;
}

pub struct WindowsHelloProvider;

impl BiometricAuthProvider for WindowsHelloProvider {
    fn is_available(&self) -> bool {
        // Future Windows Hello API detection
        false
    }

    fn authenticate_biometric(&self, _prompt_message: &str) -> Result<bool, String> {
        Err("Windows Hello provider not configured.".to_string())
    }
}
