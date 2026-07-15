import threading
from typing import Dict, Any

class HealthCheckRegistry:
    """Thread-safe registry mapping standard health-check categories to verification executors."""
    _lock = threading.Lock()
    _registry: Dict[str, Any] = {}

    @classmethod
    def register(cls, name: str, check_instance: Any) -> None:
        with cls._lock:
            if name in cls._registry:
                raise ValueError(f"Health check rule already registered: {name}")
            cls._registry[name] = check_instance

    @classmethod
    def get_checks(cls) -> Dict[str, Any]:
        with cls._lock:
            return dict(cls._registry)

    @classmethod
    def clear(cls) -> None:
        with cls._lock:
            cls._registry.clear()
