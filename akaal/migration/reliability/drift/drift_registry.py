import threading
from typing import Dict, Any

class DriftRegistry:
    """Thread-safe registry for mapping schema and metadata drift scanners."""
    _lock = threading.Lock()
    _registry: Dict[str, Any] = {}

    @classmethod
    def register(cls, name: str, scanner: Any) -> None:
        with cls._lock:
            if name in cls._registry:
                raise ValueError(f"Drift scanner already registered under name: {name}")
            cls._registry[name] = scanner

    @classmethod
    def get_scanners(cls) -> Dict[str, Any]:
        with cls._lock:
            return dict(cls._registry)

    @classmethod
    def clear(cls) -> None:
        with cls._lock:
            cls._registry.clear()
