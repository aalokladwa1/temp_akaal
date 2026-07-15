import threading
from typing import Dict, Any

class SimulationRegistry:
    """Thread-safe registry to configure execution simulation estimators."""
    _lock = threading.Lock()
    _registry: Dict[str, Any] = {}

    @classmethod
    def register(cls, name: str, estimator_instance: Any) -> None:
        with cls._lock:
            if name in cls._registry:
                raise ValueError(f"Simulation estimator already registered: {name}")
            cls._registry[name] = estimator_instance

    @classmethod
    def get_simulators(cls) -> Dict[str, Any]:
        with cls._lock:
            return dict(cls._registry)

    @classmethod
    def clear(cls) -> None:
        with cls._lock:
            cls._registry.clear()
