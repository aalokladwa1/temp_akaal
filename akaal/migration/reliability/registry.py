import threading
from typing import Dict, Type, List
from akaal.migration.reliability.base import BaseReliabilityEngine

class ReliabilityEngineRegistry:
    """Thread-safe registry for validated migration reliability engines."""
    _lock = threading.Lock()
    _registry: Dict[str, Type[BaseReliabilityEngine]] = {}

    @classmethod
    def register_engine(cls, name: str, engine_class: Type[BaseReliabilityEngine]) -> None:
        """Registers a reliability engine class, verifying inheritance boundaries."""
        if not issubclass(engine_class, BaseReliabilityEngine):
            raise TypeError("Engine class must inherit from BaseReliabilityEngine")
        with cls._lock:
            if name in cls._registry:
                raise ValueError(f"Reliability Engine already registered: {name}")
            cls._registry[name] = engine_class

    @classmethod
    def get_engine(cls, name: str) -> Type[BaseReliabilityEngine]:
        with cls._lock:
            if name not in cls._registry:
                raise KeyError(f"No reliability engine registered under name: {name}")
            return cls._registry[name]

    @classmethod
    def list_engines(cls) -> List[str]:
        with cls._lock:
            return list(cls._registry.keys())

    @classmethod
    def clear(cls) -> None:
        with cls._lock:
            cls._registry.clear()
