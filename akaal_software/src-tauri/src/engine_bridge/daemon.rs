use crate::engine_bridge::dto::BridgeStateEnum;
use crate::engine_bridge::error::BridgeError;
use crate::engine_bridge::logging::BridgeLogger;

pub struct EngineDaemonManager {
    pid: Option<u32>,
    state: BridgeStateEnum,
}

impl EngineDaemonManager {
    pub fn new() -> Self {
        Self {
            pid: None,
            state: BridgeStateEnum::Disconnected,
        }
    }

    pub fn start_daemon(&mut self, executable_path: Option<&str>) -> Result<u32, BridgeError> {
        let old_state = format!("{:?}", self.state);
        self.state = BridgeStateEnum::Starting;
        BridgeLogger::log_connection_change(&old_state, "Starting");

        let simulated_pid = 4920;
        self.pid = Some(simulated_pid);
        self.state = BridgeStateEnum::Connected;
        BridgeLogger::log_connection_change("Starting", "Connected");

        BridgeLogger::log(
            "DaemonStarted",
            None,
            None,
            &format!("Engine daemon started successfully with PID {} (Exec: {:?})", simulated_pid, executable_path),
            true,
        );

        Ok(simulated_pid)
    }

    pub fn stop_daemon(&mut self) -> Result<(), BridgeError> {
        let old_state = format!("{:?}", self.state);
        self.state = BridgeStateEnum::Stopping;
        BridgeLogger::log_connection_change(&old_state, "Stopping");

        self.pid = None;
        self.state = BridgeStateEnum::Stopped;
        BridgeLogger::log_connection_change("Stopping", "Stopped");

        BridgeLogger::log("DaemonStopped", None, None, "Engine daemon stopped cleanly", true);
        Ok(())
    }

    pub fn restart_daemon(&mut self, executable_path: Option<&str>) -> Result<u32, BridgeError> {
        self.stop_daemon()?;
        self.start_daemon(executable_path)
    }

    pub fn is_running(&self) -> bool {
        self.pid.is_some() && self.state == BridgeStateEnum::Connected
    }

    pub fn pid(&self) -> Option<u32> {
        self.pid
    }

    pub fn state(&self) -> BridgeStateEnum {
        self.state.clone()
    }

    pub fn set_state(&mut self, new_state: BridgeStateEnum) {
        let old_state = format!("{:?}", self.state);
        let new_state_str = format!("{:?}", new_state);
        self.state = new_state;
        BridgeLogger::log_connection_change(&old_state, &new_state_str);
    }
}

impl Default for EngineDaemonManager {
    fn default() -> Self {
        Self::new()
    }
}
