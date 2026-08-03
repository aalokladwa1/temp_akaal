use crate::engine_bridge::dto::HeartbeatStatusDTO;
use chrono::Utc;

pub struct HeartbeatManager {
    pub interval_secs: u64,
    pub missed_pulses: u32,
    pub max_missed_pulses: u32,
    pub last_pulse_timestamp: i64,
    pub is_connected: bool,
    pub latency_ms: u32,
}

impl HeartbeatManager {
    pub fn new(interval_secs: u64, max_missed_pulses: u32) -> Self {
        Self {
            interval_secs,
            missed_pulses: 0,
            max_missed_pulses,
            last_pulse_timestamp: Utc::now().timestamp(),
            is_connected: true,
            latency_ms: 2,
        }
    }

    pub fn record_pulse(&mut self, latency_ms: u32) {
        self.missed_pulses = 0;
        self.last_pulse_timestamp = Utc::now().timestamp();
        self.is_connected = true;
        self.latency_ms = latency_ms;
    }

    pub fn register_missed_pulse(&mut self) -> (bool, bool) {
        self.missed_pulses += 1;
        let is_healthy = self.missed_pulses < self.max_missed_pulses;
        if !is_healthy {
            self.is_connected = false;
        }
        let should_reconnect = !is_healthy;
        (is_healthy, should_reconnect)
    }

    pub fn get_status(&self) -> HeartbeatStatusDTO {
        HeartbeatStatusDTO {
            is_healthy: self.is_connected && self.missed_pulses < self.max_missed_pulses,
            last_pulse_timestamp: self.last_pulse_timestamp,
            missed_pulses: self.missed_pulses,
            latency_ms: self.latency_ms,
            reconnect_active: !self.is_connected,
        }
    }

    pub fn reset(&mut self) {
        self.missed_pulses = 0;
        self.last_pulse_timestamp = Utc::now().timestamp();
        self.is_connected = true;
    }
}
