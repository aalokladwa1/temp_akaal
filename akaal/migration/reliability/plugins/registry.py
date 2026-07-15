import threading
from typing import Dict, Any, List
from akaal.migration.reliability.plugins.validator_plugin import BaseValidatorPlugin
from akaal.migration.reliability.plugins.certification_plugin import BaseCertificationPlugin
from akaal.migration.reliability.plugins.health_plugin import BaseHealthPlugin
from akaal.migration.reliability.plugins.simulation_plugin import BaseSimulationPlugin

class PluginRegistry:
    """Thread-safe registry to configure third-party validation/certification plugins."""
    _lock = threading.Lock()
    _validators: Dict[str, BaseValidatorPlugin] = {}
    _certification_rules: Dict[str, BaseCertificationPlugin] = {}
    _health_checks: Dict[str, BaseHealthPlugin] = {}
    _simulations: Dict[str, BaseSimulationPlugin] = {}

    @classmethod
    def register_validator(cls, name: str, plugin: BaseValidatorPlugin) -> None:
        if not isinstance(plugin, BaseValidatorPlugin):
            raise TypeError("Plugin must be an instance of BaseValidatorPlugin")
        with cls._lock:
            if name in cls._validators:
                raise ValueError(f"Validator plugin already registered under name: {name}")
            cls._validators[name] = plugin

    @classmethod
    def register_certification(cls, name: str, plugin: BaseCertificationPlugin) -> None:
        if not isinstance(plugin, BaseCertificationPlugin):
            raise TypeError("Plugin must be an instance of BaseCertificationPlugin")
        with cls._lock:
            if name in cls._certification_rules:
                raise ValueError(f"Certification plugin already registered under name: {name}")
            cls._certification_rules[name] = plugin

    @classmethod
    def register_health(cls, name: str, plugin: BaseHealthPlugin) -> None:
        if not isinstance(plugin, BaseHealthPlugin):
            raise TypeError("Plugin must be an instance of BaseHealthPlugin")
        with cls._lock:
            if name in cls._health_checks:
                raise ValueError(f"Health plugin already registered under name: {name}")
            cls._health_checks[name] = plugin

    @classmethod
    def register_simulation(cls, name: str, plugin: BaseSimulationPlugin) -> None:
        if not isinstance(plugin, BaseSimulationPlugin):
            raise TypeError("Plugin must be an instance of BaseSimulationPlugin")
        with cls._lock:
            if name in cls._simulations:
                raise ValueError(f"Simulation plugin already registered under name: {name}")
            cls._simulations[name] = plugin

    @classmethod
    def get_validators(cls) -> List[BaseValidatorPlugin]:
        with cls._lock:
            return list(cls._validators.values())

    @classmethod
    def get_certifiers(cls) -> List[BaseCertificationPlugin]:
        with cls._lock:
            return list(cls._certification_rules.values())

    @classmethod
    def get_health_checks(cls) -> List[BaseHealthPlugin]:
        with cls._lock:
            return list(cls._health_checks.values())

    @classmethod
    def get_simulations(cls) -> List[BaseSimulationPlugin]:
        with cls._lock:
            return list(cls._simulations.values())

    @classmethod
    def clear(cls) -> None:
        with cls._lock:
            cls._validators.clear()
            cls._certification_rules.clear()
            cls._health_checks.clear()
            cls._simulations.clear()
