import threading
from typing import Dict, Any

class CertificationRegistry:
    """Thread-safe registry to catalog compliance and naming standards rules."""
    _lock = threading.Lock()
    _registry: Dict[str, Any] = {}

    @classmethod
    def register(cls, name: str, checker: Any) -> None:
        with cls._lock:
            if name in cls._registry:
                raise ValueError(f"Compliance rule already registered under name: {name}")
            cls._registry[name] = checker

    @classmethod
    def get_rules(cls) -> Dict[str, Any]:
        with cls._lock:
            return dict(cls._registry)

    @classmethod
    def clear(cls) -> None:
        with cls._lock:
            cls._registry.clear()
