use crate::engine_bridge::error::BridgeError;

pub trait EngineTransport: Send + Sync {
    fn send_request(&self, capability: &str, payload: &str) -> Result<String, BridgeError>;
    fn is_connected(&self) -> bool;
    fn connect(&mut self) -> Result<(), BridgeError>;
    fn disconnect(&mut self) -> Result<(), BridgeError>;
    fn transport_type(&self) -> &'static str;
}

pub struct NullTransport {
    connected: bool,
}

impl NullTransport {
    pub fn new() -> Self {
        Self { connected: true }
    }
}

impl Default for NullTransport {
    fn default() -> Self {
        Self::new()
    }
}

impl EngineTransport for NullTransport {
    fn send_request(&self, capability: &str, _payload: &str) -> Result<String, BridgeError> {
        if !self.connected {
            return Err(BridgeError::EngineNotRunning("NullTransport disconnected".to_string()));
        }

        Err(BridgeError::NotYetImplemented(format!(
            "Capability '{}' is registered on Bridge Infrastructure. Engine daemon integration pending.",
            capability
        )))
    }

    fn is_connected(&self) -> bool {
        self.connected
    }

    fn connect(&mut self) -> Result<(), BridgeError> {
        self.connected = true;
        Ok(())
    }

    fn disconnect(&mut self) -> Result<(), BridgeError> {
        self.connected = false;
        Ok(())
    }

    fn transport_type(&self) -> &'static str {
        "NullTransport"
    }
}

pub struct MockTransport {
    connected: bool,
    pub mock_response: Option<String>,
    pub should_fail: bool,
}

impl MockTransport {
    pub fn new() -> Self {
        Self {
            connected: true,
            mock_response: None,
            should_fail: false,
        }
    }
}

impl Default for MockTransport {
    fn default() -> Self {
        Self::new()
    }
}

impl EngineTransport for MockTransport {
    fn send_request(&self, capability: &str, _payload: &str) -> Result<String, BridgeError> {
        if self.should_fail {
            return Err(BridgeError::TransportFailure("Simulated mock transport failure".to_string()));
        }
        if !self.connected {
            return Err(BridgeError::EngineNotRunning("MockTransport disconnected".to_string()));
        }

        if let Some(resp) = &self.mock_response {
            Ok(resp.clone())
        } else {
            Ok(format!(r#"{{"status":"BridgeReady","capability":"{}"}}"#, capability))
        }
    }

    fn is_connected(&self) -> bool {
        self.connected
    }

    fn connect(&mut self) -> Result<(), BridgeError> {
        self.connected = true;
        Ok(())
    }

    fn disconnect(&mut self) -> Result<(), BridgeError> {
        self.connected = false;
        Ok(())
    }

    fn transport_type(&self) -> &'static str {
        "MockTransport"
    }
}
