import threading
from typing import Dict, Any
from akaal.migration.models import ObjectType

class ObjectValidatorRegistry:
    """Thread-safe registry mapping target database ObjectTypes to specific validators."""
    _lock = threading.Lock()
    _registry: Dict[ObjectType, Any] = {}

    @classmethod
    def register(cls, object_type: ObjectType, validator: Any) -> None:
        from akaal.migration.reliability.validation.object_validator import BaseObjectValidator
        if not isinstance(validator, BaseObjectValidator):
            raise TypeError("Validator instance must subclass BaseObjectValidator")
        with cls._lock:
            if object_type in cls._registry:
                raise ValueError(f"Object validator already registered for type: {object_type}")
            cls._registry[object_type] = validator

    @classmethod
    def get_validator(cls, object_type: ObjectType) -> Any:
        with cls._lock:
            if object_type not in cls._registry:
                raise ValueError(f"No object validator registered for type: {object_type}")
            return cls._registry[object_type]

    @classmethod
    def clear(cls) -> None:
        with cls._lock:
            cls._registry.clear()
