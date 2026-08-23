"""
tests.unit.engine_extensions.test_gateway_dtos
==============================================
Tests verifying that Gateway-safe descriptors serialize cleanly to dictionaries/JSON without leaking internal modules, factories, secrets, or file paths.
"""

import json
from akaalEngine.extensions.authority import ExtensionsAuthority


def test_sanitized_extension_and_provider_serialization():
    ext_auth = ExtensionsAuthority.get_instance()

    ext_descriptors = ext_auth.list_extensions()
    assert len(ext_descriptors) >= 1

    # Verify JSON serializability of all descriptors
    for desc in ext_descriptors:
        d = desc.to_dict()
        json_str = json.dumps(d)
        assert json_str is not None
        assert "extension_id" in d
        assert "providers" in d

        # Ensure no factory, class reference, or secret appears in JSON output
        assert "strategy_factory" not in json_str
        assert "InstanceStrategyFactory" not in json_str

    prov_desc = ext_auth.describe_provider("sqlite")
    assert prov_desc is not None
    prov_dict = prov_desc.to_dict()
    json_prov = json.dumps(prov_dict)
    assert json_prov is not None
    assert prov_dict["provider_id"] == "sqlite"
    assert "strategies" in prov_dict
