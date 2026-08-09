use crate::engine_bridge::dto::BridgeStateEnum;
use crate::engine_bridge::error::BridgeError;
use crate::engine_bridge::logging::BridgeLogger;
use std::process::{Child, Command};

pub struct EngineDaemonManager {
    pid: Option<u32>,
    state: BridgeStateEnum,
    child_process: Option<Child>,
}

impl EngineDaemonManager {
    pub fn new() -> Self {
        Self {
            pid: None,
            state: BridgeStateEnum::Disconnected,
            child_process: None,
        }
    }

    pub fn start_daemon(&mut self, executable_path: Option<&str>) -> Result<u32, BridgeError> {
        let old_state = format!("{:?}", self.state);
        self.state = BridgeStateEnum::Starting;
        BridgeLogger::log_connection_change(&old_state, "Starting");

        let exec_cmd = executable_path.unwrap_or("python");
        let mut cmd = Command::new(exec_cmd);
        
        // Pass --ipc if running python
        if exec_cmd.contains("python") || exec_cmd.ends_with(".py") {
            cmd.arg("main.py").arg("--ipc").current_dir(r"a:\temp_akaal");
        } else if executable_path.is_none() {
            cmd.arg(r"a:\temp_akaal\main.py").arg("--ipc");
        }

        match cmd.spawn() {
            Ok(child) => {
                let pid = child.id();
                self.pid = Some(pid);
                self.child_process = Some(child);

                // Wait up to 2.5s for IPC listener socket readiness
                let endpoint = if cfg!(windows) {
                    r"\\.\pipe\akaal_engine"
                } else {
                    "/tmp/akaal_engine.sock"
                };

                let mut listener_ready = false;
                for _ in 0..25 {
                    if std::fs::OpenOptions::new().read(true).write(true).open(endpoint).is_ok() {
                        listener_ready = true;
                        break;
                    }
                    if let Some(child_ref) = self.child_process.as_mut() {
                        if let Ok(Some(exit_status)) = child_ref.try_wait() {
                            BridgeLogger::log(
                                "DaemonFailed",
                                None,
                                None,
                                &format!("Engine daemon process PID {} exited early with status: {}", pid, exit_status),
                                false,
                            );
                            break;
                        }
                    }
                    std::thread::sleep(std::time::Duration::from_millis(100));
                }

                if !listener_ready {
                    self.state = BridgeStateEnum::Disconnected;
                    BridgeLogger::log_connection_change("Starting", "Disconnected");
                    return Err(BridgeError::EngineNotRunning(format!(
                        "Engine daemon failed to open IPC endpoint '{}' within 2.5 seconds (PID {})",
                        endpoint, pid
                    )));
                }

                self.state = BridgeStateEnum::Connected;
                BridgeLogger::log_connection_change("Starting", "Connected");

                BridgeLogger::log(
                    "DaemonStarted",
                    None,
                    None,
                    &format!("Engine daemon process spawned and IPC listener confirmed ready with PID {} (Command: {:?})", pid, exec_cmd),
                    true,
                );

                Ok(pid)
            }
            Err(e) => {
                self.pid = None;
                self.state = BridgeStateEnum::Disconnected;
                BridgeLogger::log_connection_change("Starting", "Disconnected");
                BridgeLogger::log(
                    "DaemonSpawnError",
                    None,
                    None,
                    &format!("Failed to spawn engine daemon process: {}", e),
                    false,
                );
                Err(BridgeError::EngineNotRunning(format!("Failed to spawn engine daemon executable: {}", e)))
            }
        }
    }

    pub fn stop_daemon(&mut self) -> Result<(), BridgeError> {
        let old_state = format!("{:?}", self.state);
        self.state = BridgeStateEnum::Stopping;
        BridgeLogger::log_connection_change(&old_state, "Stopping");

        if let Some(mut child) = self.child_process.take() {
            let _ = child.kill();
            let _ = child.wait();
        }

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
