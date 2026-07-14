from typing import Dict, Any, Type
from akaal.core.models.enums import SystemType

class DDLGeneratorRegistry:
    """
    Registry managing association between SystemType dialects and specific DDLGenerators.
    Enforces descriptive validation errors and checks subclass compatibility.
    """
    _registry: Dict[SystemType, Type[Any]] = {}

    @classmethod
    def register(cls, system_type: SystemType, generator_class: Type[Any]) -> None:
        """Register a generator class for a given system dialect type."""
        from akaal.migration.ddl.base import BaseDDLGenerator
        
        if not isinstance(system_type, SystemType):
            raise TypeError(f"System type must be a SystemType enum. Got: {type(system_type)}")
            
        if system_type in cls._registry:
            raise ValueError(f"DDL generator already registered for system type: {system_type}")
            
        if not issubclass(generator_class, BaseDDLGenerator):
            raise TypeError(
                f"Registered generator must inherit from BaseDDLGenerator. Got: {generator_class}"
            )
            
        cls._registry[system_type] = generator_class

    @classmethod
    def get_generator(cls, system_type: Any) -> Any:
        """Instantiate and return the registered DDL generator matching the dialect."""
        resolved_type = None
        if isinstance(system_type, SystemType):
            resolved_type = system_type
        elif isinstance(system_type, str):
            for st in SystemType:
                if st.name.lower() == system_type.lower() or st.value.lower() == system_type.lower():
                    resolved_type = st
                    break
        
        if not resolved_type:
            raise KeyError(f"Unknown database dialect: '{system_type}'")
            
        generator_class = cls._registry.get(resolved_type)
        if not generator_class:
            raise ValueError(f"No DDL generator registered for system type: {resolved_type}")
        return generator_class()

    @classmethod
    def clear(cls) -> None:
        """Helper to clear registered generators between test boundaries."""
        cls._registry.clear()
