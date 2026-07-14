from abc import ABC, abstractmethod
from typing import Set
from akaal.migration.models import ObjectType, OperationType
from akaal.migration.ddl.models import TranslationResult

class BaseObjectTranslator(ABC):
    """
    Abstract Base Class for specific database object DDL translators (e.g. Tables, Columns).
    Defines capabilities metadata and translation handlers.
    """
    SUPPORTED_OBJECTS: Set[ObjectType] = set()
    SUPPORTED_OPERATIONS: Set[OperationType] = set()

    @abstractmethod
    def translate_create(self, obj, context, quoter, capabilities, builder) -> TranslationResult:
        """Translates a CREATE operation for the target database object."""
        pass

    @abstractmethod
    def translate_drop(self, obj, context, quoter, capabilities, builder) -> TranslationResult:
        """Translates a DROP operation for the target database object."""
        pass

    @abstractmethod
    def translate_alter(self, obj, context, quoter, capabilities, builder) -> TranslationResult:
        """Translates an ALTER operation for the target database object."""
        pass
