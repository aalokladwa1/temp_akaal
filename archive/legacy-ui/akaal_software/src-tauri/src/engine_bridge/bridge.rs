use crate::engine_bridge::capability_registry::CapabilityRegistry;
use crate::engine_bridge::config::BridgeConfig;
use crate::engine_bridge::daemon::EngineDaemonManager;
use crate::engine_bridge::dto::{BridgeStatusDTO, CapabilityDTO, HeartbeatStatusDTO};
use crate::engine_bridge::error::BridgeError;
use crate::engine_bridge::heartbeat::HeartbeatManager;
use crate::engine_bridge::logging::BridgeLogger;
use crate::engine_bridge::session_manager::SessionManager;
use crate::engine_bridge::transport::{EngineTransport, RealTransport};
use uuid::Uuid;

use std::sync::Arc;

pub struct EngineBridge {
    pub config: BridgeConfig,
    pub session_manager: SessionManager,
    pub daemon_manager: EngineDaemonManager,
    pub registry: CapabilityRegistry,
    pub heartbeat_manager: HeartbeatManager,
    pub transport: Arc<dyn EngineTransport>,
}

impl EngineBridge {
    pub fn new(config: BridgeConfig, transport: Arc<dyn EngineTransport>) -> Self {
        let max_req = config.max_concurrent_requests;
        let hb_interval = config.heartbeat_interval_secs;
        let max_missed = config.reconnect_attempts;

        Self {
            config,
            session_manager: SessionManager::new(max_req),
            daemon_manager: EngineDaemonManager::new(),
            registry: CapabilityRegistry::new(),
            heartbeat_manager: HeartbeatManager::new(hb_interval, max_missed),
            transport,
        }
    }

    pub fn with_default_transport(config: BridgeConfig) -> Self {
        Self::new(config, Arc::new(RealTransport::new(None)))
    }

    pub fn get_status(&self) -> BridgeStatusDTO {
        let heartbeat_ok = self.heartbeat_manager.get_status().is_healthy;
        self.session_manager.get_status(
            self.daemon_manager.state(),
            self.transport.transport_type(),
            self.registry.count(),
            self.daemon_manager.pid(),
            heartbeat_ok,
        )
    }

    pub fn start_daemon(&mut self) -> Result<u32, BridgeError> {
        let pid = self.daemon_manager.start_daemon(self.config.engine_executable_path.as_deref())?;
        self.heartbeat_manager.reset();
        Ok(pid)
    }

    pub fn stop_daemon(&mut self) -> Result<(), BridgeError> {
        self.session_manager.terminate_session()?;
        self.daemon_manager.stop_daemon()
    }

    pub fn invoke_capability(&mut self, capability_id: &str, payload: &str) -> Result<String, BridgeError> {
        let req_id = format!("req-{}", Uuid::new_v4());
        BridgeLogger::log_request_sent(capability_id, &req_id);

        if !self.registry.is_available(capability_id) {
            let err = BridgeError::CapabilityUnavailable(format!("Capability '{}' is not registered", capability_id));
            BridgeLogger::log_response_received(capability_id, &req_id, false);
            return Err(err);
        }

        self.session_manager.begin_request()?;

        let result = self.transport.send_request(capability_id, payload);

        self.session_manager.end_request();

        match &result {
            Ok(_) => BridgeLogger::log_response_received(capability_id, &req_id, true),
            Err(_) => BridgeLogger::log_response_received(capability_id, &req_id, false),
        }

        result
    }

    pub fn list_capabilities(&self) -> Vec<CapabilityDTO> {
        self.registry.list_all()
    }

    pub fn get_heartbeat_status(&self) -> HeartbeatStatusDTO {
        self.heartbeat_manager.get_status()
    }
}
