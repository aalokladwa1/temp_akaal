pub mod bridge;
pub mod capability_registry;
pub mod commands;
pub mod config;
pub mod daemon;
pub mod dto;
pub mod error;
pub mod events;
pub mod heartbeat;
pub mod logging;
pub mod session_manager;
pub mod transport;

#[cfg(test)]
mod tests;

pub use bridge::EngineBridge;
pub use commands::EngineBridgeState;
pub use config::BridgeConfig;
