from akaal.migration.ddl.objects.base import BaseObjectTranslator
from akaal.migration.ddl.objects.registry import ObjectTranslatorRegistry

# Force module evaluation to trigger registries dynamic registrations
import akaal.migration.ddl.objects.table
import akaal.migration.ddl.objects.column
import akaal.migration.ddl.objects.constraint
import akaal.migration.ddl.objects.index
import akaal.migration.ddl.objects.view
import akaal.migration.ddl.objects.sequence
import akaal.migration.ddl.objects.trigger
import akaal.migration.ddl.objects.function
import akaal.migration.ddl.objects.procedure
import akaal.migration.ddl.objects.partition
import akaal.migration.ddl.objects.synonym
import akaal.migration.ddl.objects.materialized_view
import akaal.migration.ddl.objects.identity

__all__ = [
    "BaseObjectTranslator",
    "ObjectTranslatorRegistry"
]
