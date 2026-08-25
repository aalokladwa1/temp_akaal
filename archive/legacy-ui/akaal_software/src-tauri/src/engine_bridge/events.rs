use serde::Serialize;
use tauri::Emitter;

pub struct EventRouter;

impl EventRouter {
    pub const CHANNEL_LIFECYCLE: &'static str = "akaal://engine/lifecycle";
    pub const CHANNEL_TELEMETRY: &'static str = "akaal://engine/telemetry";
    pub const CHANNEL_LOGS: &'static str = "akaal://engine/logs";
    pub const CHANNEL_DECISIONS: &'static str = "akaal://engine/decisions";
    pub const CHANNEL_APPROVAL: &'static str = "akaal://engine/approval";
    pub const CHANNEL_HEARTBEAT: &'static str = "akaal://engine/heartbeat";
    pub const CHANNEL_CONNECTION: &'static str = "akaal://engine/connection";
    pub const CHANNEL_CAPABILITY: &'static str = "akaal://engine/capability";

    pub fn emit_event<S: Serialize + Clone>(
        app_handle: Option<&tauri::AppHandle<tauri::Wry>>,
        channel: &str,
        payload: S,
    ) -> Result<(), String> {
        if let Some(app) = app_handle {
            app.emit(channel, payload)
                .map_err(|e| format!("Failed to emit event on {}: {}", channel, e))
        } else {
            Ok(())
        }
    }
}
