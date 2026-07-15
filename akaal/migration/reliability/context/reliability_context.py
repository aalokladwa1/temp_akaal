from dataclasses import dataclass, field
from typing import List, Dict, Any
from akaal.migration.models import MigrationPlan, SchemaComparisonReport, ExecutionContext
from akaal.migration.ddl.utilities.capabilities import DialectCapabilities
from akaal.migration.reliability.models.diagnostics import ReliabilityDiagnostic
from akaal.migration.reliability.context.validation_config import ValidationConfiguration
from akaal.migration.reliability.context.runtime_metadata import RuntimeMetadata

@dataclass(frozen=True)
class ReliabilityContext:
    migration_plan: MigrationPlan
    schema_report: SchemaComparisonReport
    validation_config: ValidationConfiguration
    capabilities: DialectCapabilities
    execution_context: ExecutionContext
    diagnostics: List[ReliabilityDiagnostic] = field(default_factory=list)
    runtime_metadata: RuntimeMetadata = None  # type: ignore
