"""
Akaal — Base Comparer
=====================
Defines the abstract BaseComparer class and the COMPARER_REGISTRY for auto-discovery.
"""

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, List, Type
from akaal.core.comparison.models import ComparisonContext, SchemaDifference

# Registry populated automatically by __init_subclass__ in BaseComparer
COMPARER_REGISTRY: Dict[str, Type["BaseComparer"]] = {}


class BaseComparer(ABC):
    """
    Abstract base class that every sub-comparer must implement.
    Automatically registers itself in COMPARER_REGISTRY.
    """
    OBJECT_TYPE: ClassVar[str] = ""

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        if cls.OBJECT_TYPE:
            obj_type = cls.OBJECT_TYPE.upper()
            if obj_type in COMPARER_REGISTRY:
                raise ValueError(f"Duplicate comparer registration detected for OBJECT_TYPE '{obj_type}'")
            COMPARER_REGISTRY[obj_type] = cls

    @abstractmethod
    def compare(
        self,
        expected: Any,
        actual: Any,
        context: ComparisonContext,
        **kwargs: Any,
    ) -> List[SchemaDifference]:
        """
        Compares two domain structures (expected vs actual) and returns
        a list of differences.
        """
        pass
