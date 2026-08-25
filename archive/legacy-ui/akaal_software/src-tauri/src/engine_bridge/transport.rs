use crate::engine_bridge::error::BridgeError;
use serde::{Deserialize, Serialize};
use std::fs::OpenOptions;
use std::io::{Read, Write};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Mutex};

pub trait EngineTransport: Send + Sync {
    fn send_request(&self, capability: &str, payload: &str) -> Result<String, BridgeError>;
    fn is_connected(&self) -> bool;
    fn connect(&mut self) -> Result<(), BridgeError>;
    fn disconnect(&mut self) -> Result<(), BridgeError>;
    fn transport_type(&self) -> &'static str;
}

// ── IPC Stream Abstraction ──────────────────────────────────────────

pub struct IpcStream {
    #[cfg(windows)]
    file: std::fs::File,
    #[cfg(not(windows))]
    stream: std::os::unix::net::UnixStream,
}

impl IpcStream {
    pub fn connect(endpoint: &str) -> std::io::Result<Self> {
        #[cfg(windows)]
        {
            let file = OpenOptions::new()
                .read(true)
                .write(true)
                .open(endpoint)?;
            Ok(Self { file })
        }
        #[cfg(not(windows))]
        {
            let stream = std::os::unix::net::UnixStream::connect(endpoint)?;
            Ok(Self { stream })
        }
    }
}

impl Read for IpcStream {
    fn read(&mut self, buf: &mut [u8]) -> std::io::Result<usize> {
        #[cfg(windows)]
        {
            self.file.read(buf)
        }
        #[cfg(not(windows))]
        {
            self.stream.read(buf)
        }
    }
}

impl Write for IpcStream {
    fn write(&mut self, buf: &[u8]) -> std::io::Result<usize> {
        #[cfg(windows)]
        {
            self.file.write(buf)
        }
        #[cfg(not(windows))]
        {
            self.stream.write(buf)
        }
    }

    fn flush(&mut self) -> std::io::Result<()> {
        #[cfg(windows)]
        {
            self.file.flush()
        }
        #[cfg(not(windows))]
        {
            self.stream.flush()
        }
    }
}

// ── JSON Framing Request & Response DTOs ─────────────────────────────

#[derive(Serialize)]
struct EngineRequestPacket<'a> {
    request_id: &'a str,
    capability: &'a str,
    payload: &'a str,
}

#[derive(Deserialize)]
struct EngineResponsePacket {
    #[allow(dead_code)]
    request_id: Option<String>,
    status: String,
    result: Option<serde_json::Value>,
    error: Option<String>,
}

// ── NullTransport ───────────────────────────────────────────────────

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
            return Err(BridgeError::EngineNotRunning(
                "NullTransport disconnected".to_string(),
            ));
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

// ── MockTransport ───────────────────────────────────────────────────

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
            return Err(BridgeError::TransportFailure(
                "Simulated mock transport failure".to_string(),
            ));
        }
        if !self.connected {
            return Err(BridgeError::EngineNotRunning(
                "MockTransport disconnected".to_string(),
            ));
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

// ── RealTransport (Platform Native IPC Sockets) ──────────────────────

pub struct RealTransport {
    pub endpoint: String,
    stream: Arc<Mutex<Option<IpcStream>>>,
    request_counter: AtomicU64,
}

impl RealTransport {
    pub fn new(endpoint: Option<String>) -> Self {
        let default_endpoint = if cfg!(windows) {
            r"\\.\pipe\akaal_engine".to_string()
        } else {
            "/tmp/akaal_engine.sock".to_string()
        };

        Self {
            endpoint: endpoint.unwrap_or(default_endpoint),
            stream: Arc::new(Mutex::new(None)),
            request_counter: AtomicU64::new(1),
        }
    }

    fn try_connect(&self) -> Result<(), BridgeError> {
        let mut guard = self.stream.lock().map_err(|e| {
            BridgeError::TransportFailure(format!("Failed to lock transport mutex: {}", e))
        })?;

        if guard.is_some() {
            return Ok(());
        }

        // Deterministic startup readiness gate: retry connection up to 20 times with 100ms delay (max 2.0s)
        let max_attempts = 20;
        let delay = std::time::Duration::from_millis(100);

        for attempt in 1..=max_attempts {
            match IpcStream::connect(&self.endpoint) {
                Ok(s) => {
                    *guard = Some(s);
                    return Ok(());
                }
                Err(e) => {
                    if attempt == max_attempts {
                        return Err(BridgeError::EngineNotRunning(format!(
                            "Failed to connect to IPC transport endpoint '{}' after {} attempts ({}ms): {}",
                            self.endpoint, max_attempts, max_attempts * 100, e
                        )));
                    }
                    std::thread::sleep(delay);
                }
            }
        }

        Err(BridgeError::EngineNotRunning("IPC connection readiness timeout".to_string()))
    }
}

impl EngineTransport for RealTransport {
    fn send_request(&self, capability: &str, payload: &str) -> Result<String, BridgeError> {
        // Ensure connected
        self.try_connect()?;

        let mut guard = self.stream.lock().map_err(|e| {
            BridgeError::TransportFailure(format!("Failed to lock transport mutex: {}", e))
        })?;

        let stream_ref = guard.as_mut().ok_or_else(|| {
            BridgeError::EngineNotRunning("IPC Transport stream is not connected".to_string())
        })?;

        let req_num = self.request_counter.fetch_add(1, Ordering::SeqCst);
        let req_id = format!("req-{}", req_num);

        let packet = EngineRequestPacket {
            request_id: &req_id,
            capability,
            payload,
        };

        let json_bytes = serde_json::to_vec(&packet).map_err(|e| {
            BridgeError::InvalidPayload(format!("Failed to serialize request packet: {}", e))
        })?;

        let len_header = (json_bytes.len() as u32).to_be_bytes();

        let mut outgoing_packet = Vec::with_capacity(4 + json_bytes.len());
        outgoing_packet.extend_from_slice(&len_header);
        outgoing_packet.extend_from_slice(&json_bytes);

        // Send combined single packet (4-byte length header + payload bytes)
        if let Err(e) = stream_ref.write_all(&outgoing_packet).and_then(|_| stream_ref.flush()) {
            *guard = None; // Reset broken connection
            return Err(BridgeError::TransportFailure(format!("IPC write failed: {}", e)));
        }

        // Read 4-byte big-endian length header
        let mut resp_len_buf = [0u8; 4];
        if let Err(e) = stream_ref.read_exact(&mut resp_len_buf) {
            *guard = None; // Reset broken connection
            return Err(BridgeError::TransportFailure(format!("IPC read header failed: {}", e)));
        }

        let resp_len = u32::from_be_bytes(resp_len_buf) as usize;
        if resp_len > 50 * 1024 * 1024 {
            *guard = None;
            return Err(BridgeError::InvalidPayload("IPC response length exceeds max limit of 50MB".to_string()));
        }

        let mut resp_buf = vec![0u8; resp_len];
        if let Err(e) = stream_ref.read_exact(&mut resp_buf) {
            *guard = None;
            return Err(BridgeError::TransportFailure(format!("IPC read payload failed: {}", e)));
        }

        let response: EngineResponsePacket = serde_json::from_slice(&resp_buf).map_err(|e| {
            BridgeError::InvalidPayload(format!("Failed to deserialize IPC response: {}", e))
        })?;

        if response.status == "success" {
            match response.result {
                Some(serde_json::Value::String(s)) => Ok(s),
                Some(val) => Ok(val.to_string()),
                None => Ok(r#"{"status":"success"}"#.to_string()),
            }
        } else {
            let err_msg = response.error.unwrap_or_else(|| "Unknown engine error".to_string());
            Err(BridgeError::TransportFailure(format!("Engine error for capability '{}': {}", capability, err_msg)))
        }
    }

    fn is_connected(&self) -> bool {
        if let Ok(guard) = self.stream.lock() {
            guard.is_some()
        } else {
            false
        }
    }

    fn connect(&mut self) -> Result<(), BridgeError> {
        self.try_connect()
    }

    fn disconnect(&mut self) -> Result<(), BridgeError> {
        if let Ok(mut guard) = self.stream.lock() {
            *guard = None;
        }
        Ok(())
    }

    fn transport_type(&self) -> &'static str {
        "RealTransport"
    }
}
