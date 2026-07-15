from akaal.migration.reliability.models.diagnostics import ReliabilityDiagnostic

def create_error(message: str, category: str, recommendation: str) -> ReliabilityDiagnostic:
    return ReliabilityDiagnostic(message, "ERROR", category, recommendation)

def create_warning(message: str, category: str, recommendation: str) -> ReliabilityDiagnostic:
    return ReliabilityDiagnostic(message, "WARNING", category, recommendation)

def create_info(message: str, category: str, recommendation: str) -> ReliabilityDiagnostic:
    return ReliabilityDiagnostic(message, "INFO", category, recommendation)
