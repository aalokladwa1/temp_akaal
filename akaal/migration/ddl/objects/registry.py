from typing import Dict, Any
from akaal.migration.models import ObjectType
from akaal.migration.ddl.objects.base import BaseObjectTranslator

class ObjectTranslatorRegistry:
    """
    Registry mapping database ObjectType enums to specific BaseObjectTranslator implementations.
    Strengthened with validation checks on subclass inheritance and capability metadata.
    """
    _registry: Dict[ObjectType, BaseObjectTranslator] = {}

    @classmethod
    def register(cls, object_type: ObjectType, translator: BaseObjectTranslator) -> None:
        """Registers a translator instance mapping to an ObjectType with validation checks."""
        if not isinstance(object_type, ObjectType):
            raise TypeError(f"Invalid object_type classification: {type(object_type)}")
            
        if object_type in cls._registry:
            raise ValueError(f"Object translator already registered for type: {object_type}")
            
        if not isinstance(translator, BaseObjectTranslator):
            raise TypeError(
                f"Registered translator must subclass BaseObjectTranslator. Got: {type(translator)}"
            )
            
        if object_type not in translator.SUPPORTED_OBJECTS:
            raise ValueError(
                f"Translator capability metadata violation: {translator.__class__.__name__} "
                f"does not list support for ObjectType: {object_type}"
            )
            
        cls._registry[object_type] = translator

    @classmethod
    def get_translator(cls, object_type: ObjectType) -> BaseObjectTranslator:
        """Retrieves the registered translator instance for the given ObjectType."""
        translator = cls._registry.get(object_type)
        if not translator:
            raise ValueError(f"No object translator registered for type: {object_type}")
        return translator

    @classmethod
    def clear(cls) -> None:
        """Helper utility to reset registry between test boundaries."""
        cls._registry.clear()
