"""
Unit Tests for Runtime Capability Discovery.
"""

from akaal.performance.discovery.capability import RuntimeCapabilityDiscovery


def test_capability_discovery():
    discovery = RuntimeCapabilityDiscovery()
    
    # Verify capabilities dictionary
    caps = discovery.get_capabilities()
    assert "ram" in caps
    assert "ssd" in caps

    # Verify override capability works correctly
    discovery.override_capability("avx512", active=True, properties={"cores": 8})
    assert discovery.is_active("avx512") is True

    caps2 = discovery.get_capabilities()
    assert "avx512" in caps2
    assert caps2["avx512"].properties["cores"] == 8
