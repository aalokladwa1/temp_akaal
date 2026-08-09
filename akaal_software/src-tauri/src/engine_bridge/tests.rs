#[cfg(test)]
mod tests {
    use crate::engine_bridge::bridge::EngineBridge;
    use crate::engine_bridge::config::BridgeConfig;
    use crate::engine_bridge::dto::BridgeStateEnum;
    use crate::engine_bridge::error::BridgeError;
    use crate::engine_bridge::transport::{MockTransport, NullTransport};

    use std::sync::Arc;

    #[test]
    fn test_null_transport_returns_not_implemented() {
        let config = BridgeConfig::default();
        let mut bridge = EngineBridge::new(config, Arc::new(NullTransport::new()));

        let result = bridge.invoke_capability("test_connection", "{}");
        assert!(matches!(result, Err(BridgeError::NotYetImplemented(_))));
    }

    #[test]
    fn test_mock_transport_success() {
        let config = BridgeConfig::default();
        let mut mock = MockTransport::new();
        mock.mock_response = Some(r#"{"status":"OK","connected":true}"#.to_string());

        let mut bridge = EngineBridge::new(config, Arc::new(mock));
        let result = bridge.invoke_capability("test_connection", "{}");

        assert!(result.is_ok());
        assert_eq!(result.unwrap(), r#"{"status":"OK","connected":true}"#);
    }

    #[test]
    fn test_mock_transport_failure() {
        let config = BridgeConfig::default();
        let mut mock = MockTransport::new();
        mock.should_fail = true;

        let mut bridge = EngineBridge::new(config, Arc::new(mock));
        let result = bridge.invoke_capability("test_connection", "{}");

        assert!(matches!(result, Err(BridgeError::TransportFailure(_))));
    }

    #[test]
    fn test_concurrent_ipc_invocations() {
        let config = BridgeConfig::default();
        let mut mock = MockTransport::new();
        mock.mock_response = Some(r#"{"status":"OK","concurrent":true}"#.to_string());
        let bridge = std::sync::Arc::new(std::sync::Mutex::new(EngineBridge::new(config, Arc::new(mock))));

        let handles: Vec<_> = (0..5).map(|_| {
            let b = bridge.clone();
            std::thread::spawn(move || {
                let transport = b.lock().unwrap().transport.clone();
                transport.send_request("get_runtime_snapshot", "{}")
            })
        }).collect();

        for h in handles {
            let res = h.join().unwrap();
            assert!(res.is_ok());
        }
    }

    #[test]
    fn test_unregistered_capability_fails() {
        let config = BridgeConfig::default();
        let mut bridge = EngineBridge::with_default_transport(config);

        let result = bridge.invoke_capability("non_existent_cap", "{}");
        assert!(matches!(result, Err(BridgeError::CapabilityUnavailable(_))));
    }

    #[test]
    fn test_daemon_lifecycle() {
        let config = BridgeConfig::default();
        let mut bridge = EngineBridge::with_default_transport(config);

        assert_eq!(bridge.get_status().state, BridgeStateEnum::Disconnected);

        let pid = bridge.start_daemon();
        assert!(pid.is_ok());
        assert_eq!(bridge.get_status().state, BridgeStateEnum::Connected);

        let stop = bridge.stop_daemon();
        assert!(stop.is_ok());
        assert_eq!(bridge.get_status().state, BridgeStateEnum::Stopped);
    }

    #[test]
    fn test_capability_registry_listing() {
        let config = BridgeConfig::default();
        let bridge = EngineBridge::with_default_transport(config);

        let caps = bridge.list_capabilities();
        assert_eq!(caps.len(), 15);
        assert!(caps.iter().any(|c| c.id == "start_scout"));
        assert!(caps.iter().any(|c| c.id == "generate_plan"));
    }
}
