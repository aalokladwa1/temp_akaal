from typing import Any
from akaal.migration.models import MigrationObject

def objects_equal(obj_a: MigrationObject, obj_b: MigrationObject) -> bool:
    """Performs logic checks on migration object attributes."""
    if obj_a is None or obj_b is None:
        return obj_a == obj_b
    if type(obj_a) is not type(obj_b):
        return False
    return obj_a.name == obj_b.name and obj_a.schema == obj_b.schema
