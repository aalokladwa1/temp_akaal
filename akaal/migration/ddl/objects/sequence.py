from typing import Dict, Any
from akaal.migration.models import ObjectType, OperationType, Sequence
from akaal.migration.ddl.models import TranslationResult
from akaal.migration.ddl.objects.base import BaseObjectTranslator
from akaal.migration.ddl.objects.registry import ObjectTranslatorRegistry

class SequenceTranslator(BaseObjectTranslator):
    """Translator for Sequence database objects."""
    SUPPORTED_OBJECTS = {ObjectType.SEQUENCE}
    SUPPORTED_OPERATIONS = {OperationType.CREATE, OperationType.DROP}

    def translate_create(self, obj: Sequence, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        schema_prefix = f"{quoter.quote(obj.schema)}." if obj.schema else ""
        quoted_name = quoter.quote(obj.name)
        full_seq_name = f"{schema_prefix}{quoted_name}"
        
        start = getattr(obj, "start_value", None)
        increment = getattr(obj, "increment_by", None)
        
        # Sequencers can only use increment options if supported by target capabilities
        if not capabilities.supports_sequence_increment:
            start = None
            increment = None
            
        sql = builder.build_create_sequence(full_seq_name, start=start, increment=increment)
        rollback_sql = builder.build_drop_sequence(full_seq_name)
        
        return TranslationResult(sql=sql, rollback_sql=rollback_sql)

    def translate_drop(self, obj: Sequence, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        schema_prefix = f"{quoter.quote(obj.schema)}." if obj.schema else ""
        quoted_name = quoter.quote(obj.name)
        full_seq_name = f"{schema_prefix}{quoted_name}"
        
        sql = builder.build_drop_sequence(full_seq_name)
        rollback_sql = builder.build_create_sequence(full_seq_name)
        
        return TranslationResult(sql=sql, rollback_sql=rollback_sql)

    def translate_alter(self, obj: Sequence, context: Dict[str, Any], quoter, capabilities, builder) -> TranslationResult:
        warnings = (f"Unsupported ALTER operation on Sequence object '{obj.name}'",)
        return TranslationResult(sql="", warnings=warnings)

# Register the sequence translator instance
ObjectTranslatorRegistry.register(ObjectType.SEQUENCE, SequenceTranslator())
