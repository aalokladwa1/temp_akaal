pub mod administration;
pub mod authentication;
pub mod events;
pub mod migration;
pub mod security;
pub mod session;
pub mod system;

pub use events::{AuditCategory, AuditEvent, AuditSeverity};
use std::sync::{Mutex, OnceLock};

pub struct AuditEngine {
    events: Mutex<Vec<AuditEvent>>,
}

impl AuditEngine {
    pub fn new() -> Self {
        Self {
            events: Mutex::new(Vec::new()),
        }
    }

    pub fn global() -> &'static AuditEngine {
        static INSTANCE: OnceLock<AuditEngine> = OnceLock::new();
        INSTANCE.get_or_init(AuditEngine::new)
    }

    pub fn log_event(&self, event: AuditEvent) {
        println!(
            "[AUDIT LOG] [{:?}] [{}] - {:?}",
            event.category, event.event_type, event.details
        );
        if let Ok(mut guard) = self.events.lock() {
            guard.push(event);
        }
    }

    pub fn get_events(&self) -> Vec<AuditEvent> {
        if let Ok(guard) = self.events.lock() {
            return guard.clone();
        }
        Vec::new()
    }
}
