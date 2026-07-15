import threading
from typing import Dict, Any

class RollbackRegistry:
    """Thread-safe registry for registering custom rollback strategies and validators."""
    _lock = threading.Lock()
    _registry: Dict[str, Any] = {}

    @classmethod
    def register(cls, name: str, strategy: Any) -> None:
        with cls._lock:
            if name in cls._registry:
                raise ValueError(f"Rollback strategy already registered: {name}")
            cls._registry[name] = strategy

    @classmethod
    def get_strategies(cls) -> Dict[str, Any]:
        with cls._lock:
            return dict(cls._registry)

    @classmethod
    def clear(cls) -> None:
        with cls._lock:
            cls._registry.clear()
