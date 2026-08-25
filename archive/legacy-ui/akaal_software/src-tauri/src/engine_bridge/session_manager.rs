use crate::engine_bridge::dto::{BridgeStateEnum, BridgeStatusDTO, RuntimeSessionDTO};
use crate::engine_bridge::error::BridgeError;
use chrono::Utc;
use uuid::Uuid;

pub struct SessionManager {
    current_session_id: Option<String>,
    active_session: Option<RuntimeSessionDTO>,
    outstanding_requests_count: u32,
    max_concurrent_requests: u32,
    is_cancelled: bool,
    start_timestamp: i64,
}

impl SessionManager {
    pub fn new(max_concurrent_requests: u32) -> Self {
        Self {
            current_session_id: None,
            active_session: None,
            outstanding_requests_count: 0,
            max_concurrent_requests,
            is_cancelled: false,
            start_timestamp: Utc::now().timestamp(),
        }
    }

    pub fn create_session(&mut self, migration_id: &str) -> RuntimeSessionDTO {
        let session_id = format!("sess-{}", Uuid::new_v4());
        let session = RuntimeSessionDTO {
            session_id: session_id.clone(),
            migration_id: migration_id.to_string(),
            execution_number: 1,
            status: "initializing".to_string(),
            current_stage: "scout".to_string(),
            progress_percent: 0,
            started_at: Utc::now().to_rfc3339(),
        };

        self.current_session_id = Some(session_id);
        self.active_session = Some(session.clone());
        self.is_cancelled = false;
        session
    }

    pub fn terminate_session(&mut self) -> Result<(), BridgeError> {
        self.current_session_id = None;
        self.active_session = None;
        self.outstanding_requests_count = 0;
        self.is_cancelled = false;
        Ok(())
    }

    pub fn begin_request(&mut self) -> Result<(), BridgeError> {
        if self.is_cancelled {
            return Err(BridgeError::Cancelled("Operation cancelled by user".to_string()));
        }
        if self.outstanding_requests_count >= self.max_concurrent_requests {
            return Err(BridgeError::TransportFailure("Max concurrent requests reached".to_string()));
        }
        self.outstanding_requests_count += 1;
        Ok(())
    }

    pub fn end_request(&mut self) {
        if self.outstanding_requests_count > 0 {
            self.outstanding_requests_count -= 1;
        }
    }

    pub fn cancel_current_operation(&mut self) {
        self.is_cancelled = true;
    }

    pub fn get_status(
        &self,
        bridge_state: BridgeStateEnum,
        transport_type: &str,
        capabilities_count: usize,
        pid: Option<u32>,
        heartbeat_ok: bool,
    ) -> BridgeStatusDTO {
        let uptime = (Utc::now().timestamp() - self.start_timestamp).max(0) as u64;

        BridgeStatusDTO {
            state: bridge_state,
            engine_pid: pid,
            active_session_id: self.current_session_id.clone(),
            transport_type: transport_type.to_string(),
            heartbeat_ok,
            uptime_seconds: uptime,
            registered_capabilities_count: capabilities_count,
        }
    }
}
